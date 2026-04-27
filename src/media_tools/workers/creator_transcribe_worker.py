from __future__ import annotations

import asyncio
import logging
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from media_tools.common.paths import get_download_path
from media_tools.db.core import get_db_connection
from media_tools.repositories.task_repository import TaskRepository
from media_tools.services.asset_file_ops import _resolve_asset_video_file, get_source_url_column
from media_tools.services.task_ops import update_task_progress, _fail_task
from media_tools.workers.local_transcribe_worker import _background_local_transcribe_worker

logger = logging.getLogger(__name__)


def _normalize_stem(value: str) -> str:
    return re.sub(r"_[0-9]+$", "", value or "")


@dataclass(frozen=True, slots=True)
class _LocalReq:
    file_paths: list[str]
    delete_after: bool = False
    directory_root: str | None = None


def _discover_creator_files(uid: str) -> tuple[list[str], list[str]]:
    download_dir = get_download_path()
    file_paths: list[str] = []
    not_found: list[str] = []

    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            source_url_select = get_source_url_column(conn)
            cursor = conn.execute(
                f"""SELECT asset_id, creator_uid, {source_url_select} video_path
                    FROM media_assets
                    WHERE creator_uid = ?
                      AND video_status IN ('downloaded', 'pending')
                      AND transcript_status IN ('pending', 'none', 'failed')
                    """,
                (uid,),
            )
            for row in cursor.fetchall():
                resolved = _resolve_asset_video_file(
                    creator_uid=row["creator_uid"],
                    source_url=row["source_url"],
                    video_path=row["video_path"],
                    download_dir=download_dir,
                )
                if resolved and resolved.exists():
                    file_paths.append(str(resolved))
                    continue

                video_path = row["video_path"] or ""
                filename = Path(video_path).name if video_path else ""
                if not filename:
                    continue

                found = None
                stem = Path(filename).stem
                for match in download_dir.rglob(f"{stem}*.mp4"):
                    if match.is_file():
                        found = match
                        break
                if not found:
                    for match in download_dir.rglob(f"{stem}*"):
                        if match.is_file() and match.suffix.lower() in (".mp4", ".webm", ".mkv", ".avi", ".mov"):
                            found = match
                            break

                if found:
                    file_paths.append(str(found))
                    try:
                        new_rel = str(found.relative_to(download_dir))
                        conn.execute(
                            "UPDATE media_assets SET video_path = ? WHERE asset_id = ?",
                            (new_rel, row["asset_id"]),
                        )
                    except (ValueError, sqlite3.Error):
                        pass
                else:
                    not_found.append(filename)
    except (sqlite3.Error, OSError) as e:
        raise RuntimeError(f"查询待转写素材失败: {e}") from e

    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT DISTINCT folder_path FROM media_assets WHERE creator_uid = ? AND folder_path IS NOT NULL",
                (uid,),
            )
            folder_names = [row["folder_path"] for row in cursor.fetchall() if row["folder_path"]]

            cursor2 = conn.execute("SELECT nickname FROM creators WHERE uid = ?", (uid,))
            nickname_row = cursor2.fetchone()
            if nickname_row and nickname_row["nickname"]:
                folder_names.append(nickname_row["nickname"])

        completed_stems: set[str] = set()
        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT video_path FROM media_assets WHERE creator_uid = ? AND video_path IS NOT NULL AND video_path != ''",
                (uid,),
            )
            for row in cursor.fetchall():
                vp = row["video_path"] or ""
                if vp:
                    completed_stems.add(_normalize_stem(Path(vp).stem))

        for folder_name in folder_names:
            folder = download_dir / folder_name
            if not folder.is_dir():
                continue
            for f in folder.glob("*.mp4"):
                if _normalize_stem(f.stem) in completed_stems:
                    continue
                file_paths.append(str(f))
                try:
                    import uuid as _uuid

                    asset_id = str(_uuid.uuid5(_uuid.NAMESPACE_URL, str(f.resolve())))
                    now = datetime.now().isoformat()
                    with get_db_connection() as conn:
                        conn.execute(
                            """INSERT OR IGNORE INTO media_assets
                               (asset_id, creator_uid, title, video_path, video_status, transcript_status, folder_path, create_time, update_time)
                               VALUES (?, ?, ?, ?, 'downloaded', 'pending', ?, ?, ?)""",
                            (
                                asset_id,
                                uid,
                                f.stem,
                                str(f.relative_to(download_dir)),
                                folder_name,
                                now,
                                now,
                            ),
                        )
                except (sqlite3.Error, OSError, ValueError):
                    pass
    except (sqlite3.Error, OSError) as e:
        logger.warning(f"扫描下载目录失败: {e}")

    if file_paths:
        try:
            with get_db_connection() as conn:
                conn.execute(
                    """UPDATE media_assets SET transcript_status = 'pending'
                       WHERE creator_uid = ? AND transcript_status = 'none'
                          AND video_status IN ('downloaded', 'pending')""",
                    (uid,),
                )
        except sqlite3.Error:
            pass

    return file_paths, not_found


async def background_creator_transcribe_worker(task_id: str, uid: str) -> None:
    try:
        await update_task_progress(task_id, 0.01, "正在扫描待转写文件...", "local_transcribe", stage="scanning")
        file_paths, not_found = await asyncio.to_thread(_discover_creator_files, uid)
    except Exception as e:
        await _fail_task(task_id, "local_transcribe", str(e))
        return

    if not file_paths:
        message = (
            f"该博主有 {len(not_found)} 个待转写素材，但视频文件在磁盘上找不到"
            if not_found
            else "该博主没有待转写的素材"
        )
        await _fail_task(task_id, "local_transcribe", message)
        return

    TaskRepository.patch_payload(task_id, {"creator_uid": uid, "file_paths": file_paths})
    await update_task_progress(
        task_id,
        0.02,
        f"扫描完成，准备转写 {len(file_paths)} 个文件",
        "local_transcribe",
        stage="queued",
    )

    req = _LocalReq(file_paths=file_paths)
    await _background_local_transcribe_worker(task_id, req)
