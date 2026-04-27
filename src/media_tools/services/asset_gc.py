from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def cleanup_stale_assets(conn: sqlite3.Connection) -> dict[str, int]:
    deleted_assets = conn.execute("SELECT asset_id FROM media_assets WHERE video_status='deleted'").fetchall()
    deleted_count = 0
    if deleted_assets:
        deleted_ids = [row[0] for row in deleted_assets]
        placeholders = ",".join("?" * len(deleted_ids))
        conn.execute(f"DELETE FROM assets_fts WHERE asset_id IN ({placeholders})", deleted_ids)
        conn.execute(f"DELETE FROM media_assets WHERE asset_id IN ({placeholders})", deleted_ids)
        deleted_count = len(deleted_ids)
        logger.info(f"Cleaned up {deleted_count} deleted media assets")

    stale_pending_cutoff = (datetime.now() - timedelta(days=30)).isoformat()
    stale_assets = conn.execute(
        "SELECT asset_id FROM media_assets WHERE transcript_status='pending' AND create_time < ?",
        (stale_pending_cutoff,),
    ).fetchall()
    stale_pending_count = 0
    if stale_assets:
        stale_ids = [row[0] for row in stale_assets]
        placeholders = ",".join("?" * len(stale_ids))
        conn.execute(f"DELETE FROM assets_fts WHERE asset_id IN ({placeholders})", stale_ids)
        conn.execute(f"DELETE FROM media_assets WHERE asset_id IN ({placeholders})", stale_ids)
        stale_pending_count = len(stale_ids)
        logger.info(f"Cleaned up {stale_pending_count} stale pending media assets")

    conn.commit()
    return {"deleted_assets": deleted_count, "stale_pending_assets": stale_pending_count}

