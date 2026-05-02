import asyncio
import sqlite3
from media_tools.core.logging_context import task_context
from media_tools.db.core import get_db_connection
from media_tools.douyin.core.cancel_registry import clear_download_progress, get_download_progress
from media_tools.douyin.core.downloader import download_by_uid
from media_tools.douyin.core.following_mgr import list_users
from media_tools.services.task_ops import update_task_progress, _complete_task
from media_tools.services.task_state import _task_heartbeat
from media_tools.workers.creator_sync import _build_interval_from_last_fetch


async def _background_full_sync_worker(task_id: str, mode: str = "incremental", batch_size: int | None = None, original_params: dict | None = None):
    async def _progress_fn(p, m, result_summary=None, subtasks=None, stage=""):
        await update_task_progress(task_id, p, m, f"full_sync_{mode}", result_summary, subtasks, stage)

    heartbeat = asyncio.create_task(_task_heartbeat(task_id))
    try:
        with task_context(task_id=task_id):
            users = list_users()
            if not users:
                msg = "关注列表为空"
                await _complete_task(task_id, f"full_sync_{mode}", msg, status="COMPLETED")
                return

            total = len(users)
            creator_success = 0
            creator_failed = 0
            new_video_count = 0
            skip_existing = True  # 始终跳过已存在的

            for index, user in enumerate(users, 1):
                uid = user.get("uid") or ""
                name = user.get("nickname") or user.get("name") or uid or f"creator-{index}"
                await _progress_fn((index - 1) / total, f"正在同步 {name} ({index}/{total}) [{mode}]", stage="downloading")

                # 增量模式：根据 last_fetch_time 计算 interval
                interval = None
                if mode == "incremental":
                    with get_db_connection() as conn:
                        cursor = conn.execute(
                            "SELECT last_fetch_time FROM creators WHERE uid = ?",
                            (uid,),
                        )
                        row = cursor.fetchone()
                        last_fetch = (row["last_fetch_time"] if isinstance(row, dict) else row[0]) if row else None
                    interval = _build_interval_from_last_fetch(last_fetch)

                existing_source = "file" if mode == "full" else "file+db"

                try:
                    dl_task = asyncio.create_task(
                        asyncio.to_thread(download_by_uid, uid, batch_size, skip_existing, task_id, interval, existing_source)
                    )

                    async def _poll_creator():
                        while True:
                            await asyncio.sleep(5)
                            info = get_download_progress(task_id)
                            if info:
                                d = info.get("downloaded", 0)
                                s = info.get("skipped", 0)
                                details = info.get("details", [])
                                subtasks = [
                                    {"title": d_.get("title", "未知")[:60], "status": d_.get("status", "unknown")}
                                    for d_ in details[-50:]
                                ]
                                await update_task_progress(
                                    task_id,
                                    (index - 1) / total + 0.5 / total * min(d / max(batch_size or 50, 1), 1.0),
                                    f"{name}：已下载 {d} 个，跳过 {s} 个",
                                    f"full_sync_{mode}",
                                    subtasks=subtasks,
                                )

                    poll_task = asyncio.create_task(_poll_creator())
                    try:
                        result = await dl_task
                    finally:
                        poll_task.cancel()
                        try:
                            await poll_task
                        except asyncio.CancelledError:
                            pass
                        clear_download_progress(task_id)

                    if isinstance(result, dict) and result.get("success"):
                        creator_success += 1
                        new_video_count += len(result.get("new_files") or [])
                        # 更新 last_fetch_time，避免下次重复拉取全部列表
                        try:
                            from datetime import datetime
                            with get_db_connection() as conn:
                                conn.execute(
                                    "UPDATE creators SET last_fetch_time = ? WHERE uid = ?",
                                    (datetime.now().isoformat(), uid),
                                )
                        except sqlite3.Error:
                            pass
                    else:
                        creator_failed += 1
                except (RuntimeError, OSError, asyncio.CancelledError) as exc:
                    creator_failed += 1
                    await update_task_progress(task_id, (index - 1) / total, f"{name} 同步失败: {exc}", f"full_sync_{mode}")
                finally:
                    await update_task_progress(task_id, index / total, f"已完成 {name} ({index}/{total})", f"full_sync_{mode}")

            result_summary = {
                "success": creator_success,
                "failed": creator_failed,
                "skipped": 0,
                "total": total,
            }
            msg = f"全量同步完成：成功 {creator_success} 位，失败 {creator_failed} 位，新增 {new_video_count} 个视频（{mode}）"
            await _complete_task(task_id, f"full_sync_{mode}", msg, status="COMPLETED", result_summary=result_summary)
    except asyncio.CancelledError:
        raise
    except (RuntimeError, OSError) as e:
        await _complete_task(task_id, f"full_sync_{mode}", str(e), status="FAILED", error_msg=str(e))
    finally:
        heartbeat.cancel()
        try:
            await heartbeat
        except asyncio.CancelledError:
            pass
