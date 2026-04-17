"""Backfill missing transcript_preview / transcript_text in the background.

New transcripts write both inline (orchestrator / local worker). This module
handles existing rows that predate those columns.
"""
import sqlite3
import threading
from pathlib import Path

from media_tools.db.core import get_db_connection
from media_tools.logger import get_logger
from media_tools.pipeline.preview import extract_transcript_preview, extract_transcript_text

logger = get_logger("preview_backfill")

_BATCH = 50
_started = False
_lock = threading.Lock()


def _transcripts_dir() -> Path:
    from media_tools.douyin.core.config_mgr import get_config
    return get_config().project_root / "transcripts"


def _run() -> None:
    base_dir = _transcripts_dir()
    total = 0
    try:
        while True:
            with get_db_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT asset_id, transcript_path FROM media_assets
                    WHERE transcript_status = 'completed'
                      AND transcript_path IS NOT NULL AND transcript_path != ''
                      AND (transcript_preview IS NULL OR transcript_text IS NULL)
                    LIMIT ?
                    """,
                    (_BATCH,),
                )
                rows = cursor.fetchall()
            if not rows:
                break
            updates: list[tuple[str, str, str]] = []
            for row in rows:
                file_path = base_dir / row["transcript_path"]
                preview = extract_transcript_preview(file_path)
                full_text = extract_transcript_text(file_path)
                updates.append((preview, full_text, row["asset_id"]))
            with get_db_connection() as conn:
                conn.executemany(
                    "UPDATE media_assets SET transcript_preview = ?, transcript_text = ? WHERE asset_id = ?",
                    updates,
                )
                conn.commit()
            total += len(updates)
        if total:
            logger.info(f"Backfilled transcript preview/text for {total} rows")
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Preview/text backfill aborted: {exc}")


def start_backfill_once() -> None:
    """Kick off backfill in a daemon thread; no-op on subsequent calls."""
    global _started
    with _lock:
        if _started:
            return
        _started = True
    t = threading.Thread(target=_run, name="transcript-preview-backfill", daemon=True)
    t.start()
