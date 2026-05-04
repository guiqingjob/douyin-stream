from __future__ import annotations

import asyncio
import logging
import sqlite3

from media_tools.core.config import get_runtime_setting_bool
from media_tools.core.logging_context import task_context
from media_tools.db.core import get_db_connection
from media_tools.douyin.core.downloader import download_aweme_by_url
from media_tools.services.task_ops import _complete_task, update_task_progress
from media_tools.services.task_state import _task_heartbeat
from media_tools.workers.transcribe import transcribe_files

logger = logging.getLogger(__name__)


async def recover_aweme_transcribe(task_id: str, creator_uid: str, aweme_id: str, title: str = "") -> None:
    async def _progress_fn(p, m, result_summary=None, subtasks=None, stage=""):
        await update_task_progress(task_id, p, m, "recover_aweme_transcribe", result_summary, subtasks, stage)

    heartbeat = asyncio.create_task(_task_heartbeat(task_id))
    try:
        with task_context(task_id=task_id, creator_uid=creator_uid):
            resolved_title = title.strip() if isinstance(title, str) else ""
            if not resolved_title:
                try:
                    with get_db_connection() as conn:
                        conn.row_factory = sqlite3.Row
                        row = conn.execute("SELECT desc FROM video_metadata WHERE aweme_id=? LIMIT 1", (aweme_id,)).fetchone()
                        if row and row["desc"]:
                            resolved_title = str(row["desc"]).strip()
                except (sqlite3.Error, OSError, TypeError, ValueError):
                    resolved_title = ""

            display_name = resolved_title or creator_uid or aweme_id

            await _progress_fn(0.05, f"补齐下载：{display_name}", stage="downloading")
            url = f"https://www.douyin.com/video/{aweme_id}"
            dl = await download_aweme_by_url(url)
            if not isinstance(dl, dict) or not dl.get("success"):
                raise RuntimeError(f"补齐下载失败: {dl!r}")

            new_files = dl.get("new_files") or []
            if not isinstance(new_files, list) or not new_files:
                raise RuntimeError("补齐下载未产生新文件")

            auto_delete = get_runtime_setting_bool("auto_delete", True)
            tr = await transcribe_files(task_id, _progress_fn, list(new_files), display_name, auto_delete=auto_delete)

            s = int(tr.get("success_count", 0) or 0)
            f = int(tr.get("failed_count", 0) or 0)
            total = int(tr.get("total", s + f) or (s + f))
            subtasks = tr.get("subtasks") or []
            result_summary = tr.get("result_summary") or {"success": s, "failed": f, "skipped": 0, "total": total}

            msg = f"补齐并转写完成：成功 {s} 个，失败 {f} 个"
            if f == 0:
                await _complete_task(
                    task_id,
                    "recover_aweme_transcribe",
                    msg,
                    status="COMPLETED",
                    result_summary=result_summary,
                    subtasks=subtasks,
                )
                return

            error_msg = msg
            if isinstance(subtasks, list) and subtasks:
                first = subtasks[0] if isinstance(subtasks[0], dict) else {}
                err = first.get("error") if isinstance(first, dict) else None
                if err:
                    error_msg = str(err)

            await _complete_task(
                task_id,
                "recover_aweme_transcribe",
                msg,
                status="FAILED",
                error_msg=error_msg,
                result_summary=result_summary,
                subtasks=subtasks,
            )
    except asyncio.CancelledError:
        raise
    except (OSError, RuntimeError, ValueError, TypeError, sqlite3.Error) as e:
        await _complete_task(task_id, "recover_aweme_transcribe", str(e), status="FAILED", error_msg=str(e))
    finally:
        heartbeat.cancel()
        try:
            await heartbeat
        except asyncio.CancelledError:
            pass

