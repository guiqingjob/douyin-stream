"""创作者同步工作者"""
from __future__ import annotations

import asyncio
import logging
import sqlite3
from typing import Any

from media_tools.api.routers.tasks import (
    _get_global_setting_bool,
    _merge_payload_from_db,
    _task_heartbeat,
    clear_download_progress,
    get_download_progress,
    notify_task_update,
    update_task_progress,
)
from media_tools.db.core import get_db_connection
from media_tools.workers.transcribe import transcribe_files

logger = logging.getLogger(__name__)


async def background_creator_download_worker(
    task_id: str,
    uid: str,
    mode: str = "incremental",
    batch_size: int | None = None,
    original_params: dict | None = None,
):
    """创作者同步 Worker - 下载 + 自动转写"""

    async def _progress_fn(p, m, result_summary=None, subtasks=None, stage=""):
        await update_task_progress(task_id, p, m, f"creator_sync_{mode}", result_summary, subtasks, stage)

    heartbeat = asyncio.create_task(_task_heartbeat(task_id))
    try:
        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT uid, sec_user_id, nickname, platform FROM creators WHERE uid = ? LIMIT 1",
                (uid,),
            )
            creator_row = cursor.fetchone()

        if not creator_row:
            raise RuntimeError(f"Creator not found: {uid}")

        platform = (creator_row.get("platform") if isinstance(creator_row, dict) else creator_row["platform"]) or "douyin"
        sec_user_id = (creator_row.get("sec_user_id") if isinstance(creator_row, dict) else creator_row["sec_user_id"]) or ""
        display_name = (creator_row.get("nickname") if isinstance(creator_row, dict) else creator_row["nickname"]) or uid

        requested_batch_size = batch_size
        douyin_batch_size = batch_size or 50
        batch_label = requested_batch_size if requested_batch_size is not None else ("全部" if platform == "bilibili" else douyin_batch_size)
        await _progress_fn(0.05, f"开始同步 {display_name} 的视频（{mode}，每批 {batch_label} 个）...", stage="initializing")

        skip_existing = (original_params or {}).get("_resumed") or mode != "full"
        total_downloaded = 0
        batch_num = 1
        completed_batches = 0
        all_new_files: list[str] = []
        last_result: dict[str, Any] = {}
        transcribe_stats = {"success_count": 0, "failed_count": 0, "total": 0}
        all_subtasks: list[dict] = []

        while True:
            current_batch_size = requested_batch_size if platform == "bilibili" else douyin_batch_size
            await _progress_fn(0.1, f"第 {batch_num} 批：下载中（最多 {current_batch_size or '全部'} 个）...", stage="downloading")

            if platform == "bilibili":
                from media_tools.bilibili.core.downloader import download_up_by_url

                mid = sec_user_id or uid.split(":", 1)[-1]
                url = f"https://space.bilibili.com/{mid}"
                try:
                    result = await asyncio.to_thread(download_up_by_url, url, current_batch_size, skip_existing, None, task_id)
                except Exception as e:
                    error_msg = str(e)
                    if "412" in error_msg or "blocked" in error_msg.lower():
                        await _progress_fn(0.5, f"B站请求被拦截(412)，请更换IP或稍后重试", stage="downloading")
                        raise RuntimeError(f"B站请求被拦截(412)，请更换IP或稍后重试: {error_msg}")
                    raise
                completed_batches += 1
                if isinstance(result, dict):
                    last_result = result
                new_files = (result.get("new_files") or []) if isinstance(result, dict) else []

                auto_transcribe = _get_global_setting_bool("auto_transcribe")
                auto_delete = _get_global_setting_bool("auto_delete")
                if auto_transcribe and new_files:
                    tr = await transcribe_files(task_id, _progress_fn, new_files, display_name, auto_delete)
                    transcribe_stats["success_count"] += tr.get("success_count", 0)
                    transcribe_stats["failed_count"] += tr.get("failed_count", 0)
                    transcribe_stats["total"] += tr.get("total", 0)
                    all_subtasks.extend(tr.get("subtasks", []))

                total_downloaded += len(new_files)
                all_new_files.extend(new_files)
                break

            else:
                from media_tools.douyin.core.downloader import download_by_url

                if sec_user_id.startswith("MS4w"):
                    url = f"https://www.douyin.com/user/{sec_user_id}"
                else:
                    url = f"https://www.douyin.com/user/{uid}"

                dl_task = asyncio.create_task(
                    asyncio.to_thread(download_by_url, url, current_batch_size, False, skip_existing, task_id)
                )

                async def _poll():
                    while True:
                        await asyncio.sleep(5)
                        info = get_download_progress(task_id)
                        if info:
                            d = info.get("downloaded", 0)
                            s = info.get("skipped", 0)
                            p = info.get("page", batch_num)
                            details = info.get("details", [])
                            subtasks = [
                                {"title": d_.get("title", "未知")[:60], "status": d_.get("status", "unknown")}
                                for d_ in details[-50:]
                            ]
                            await update_task_progress(
                                task_id,
                                0.1 + 0.3 * min(d / max(current_batch_size or 50, 1), 1.0),
                                f"第 {p} 批：已下载 {d} 个，跳过 {s} 个",
                                f"creator_sync_{mode}",
                                subtasks=subtasks,
                                stage="downloading",
                            )

                poll_task = asyncio.create_task(_poll())
                try:
                    result = await dl_task
                finally:
                    poll_task.cancel()
                    try:
                        await poll_task
                    except asyncio.CancelledError:
                        pass
                    clear_download_progress(task_id)

                completed_batches += 1
                if isinstance(result, dict):
                    last_result = result

                if not isinstance(result, dict) or not result.get("success"):
                    logger.warning(f"下载批次 {batch_num} 失败: {result}")
                    break

                new_files = (result.get("new_files") or []) if isinstance(result, dict) else []

                auto_transcribe = _get_global_setting_bool("auto_transcribe")
                auto_delete = _get_global_setting_bool("auto_delete")
                if auto_transcribe and new_files:
                    tr = await transcribe_files(task_id, _progress_fn, new_files, display_name, auto_delete)
                    transcribe_stats["success_count"] += tr.get("success_count", 0)
                    transcribe_stats["failed_count"] += tr.get("failed_count", 0)
                    transcribe_stats["total"] += tr.get("total", 0)
                    all_subtasks.extend(tr.get("subtasks", []))

            if not skip_existing:
                break

            if not new_files:
                break

            total_downloaded += len(new_files)
            all_new_files.extend(new_files)
            batch_num += 1

            await _progress_fn(0.9, f"第 {batch_num - 1} 批完成（累计 {total_downloaded} 个），继续下一批...", stage="downloading")

        # 更新创作者信息
        if uploader := last_result.get("uploader"):
            if uploader.get("nickname"):
                with get_db_connection() as conn:
                    creator_columns = {
                        row["name"] if isinstance(row, sqlite3.Row) else row[1]
                        for row in conn.execute("PRAGMA table_info(creators)").fetchall()
                    }
                    if "homepage_url" in creator_columns:
                        conn.execute(
                            "UPDATE creators SET nickname = ?, homepage_url = ? WHERE uid = ?",
                            (uploader["nickname"], uploader.get("homepage_url", ""), uid),
                        )
                    else:
                        conn.execute(
                            "UPDATE creators SET nickname = ? WHERE uid = ?",
                            (uploader["nickname"], uid),
                        )
                    conn.commit()

        # 构建结果摘要
        result_summary = {
            "success": transcribe_stats["success_count"],
            "failed": transcribe_stats["failed_count"],
            "skipped": 0,
            "total": transcribe_stats["total"],
        }
        if transcribe_stats["total"] > 0:
            msg = f"{display_name} 同步完成：下载 {total_downloaded} 个，转写成功 {transcribe_stats['success_count']} 个，失败 {transcribe_stats['failed_count']} 个"
        else:
            msg = f"{display_name} 同步完成：共 {total_downloaded} 个新视频（{completed_batches} 批，{mode}）"
        with get_db_connection() as conn:
            payload_str = _merge_payload_from_db(conn, task_id, msg, result_summary, all_subtasks or None)
            conn.execute("UPDATE task_queue SET status='COMPLETED', progress=1.0, payload=? WHERE task_id=?", (payload_str, task_id))
            if mode == "incremental":
                conn.execute(
                    "UPDATE creators SET last_fetch_time = CURRENT_TIMESTAMP WHERE uid = ?",
                    (uid,)
                )
            conn.commit()
        await notify_task_update(task_id, 1.0, msg, "COMPLETED", f"creator_sync_{mode}", result_summary, all_subtasks or None, stage="completed")
    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.exception(f"creator_download_worker failed for {uid}")
        with get_db_connection() as conn:
            conn.execute("UPDATE task_queue SET status='FAILED', error_msg=? WHERE task_id=?", (str(e), task_id))
        await notify_task_update(task_id, 0.0, str(e), "FAILED", f"creator_sync_{mode}")
    finally:
        heartbeat.cancel()
        try:
            await heartbeat
        except asyncio.CancelledError:
            pass
