"""转写运行记录仓库 - transcribe_runs 表的所有操作

每个 run 代表一次对某个视频、在某个通义账号上的完整转写尝试。
stage 字段记录当前进行到哪一阶段，record_id / gen_record_id 在上传成功后持久化，
使得上传后任意环节失败时，下一次重试可以从 uploaded 阶段恢复，不再重传文件。
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime
from typing import Any

from media_tools.db.core import get_db_connection
from media_tools.logger import get_logger

logger = get_logger(__name__)


# 上传完成、且尚未落盘的中间阶段 —— 这些阶段的 run 可以在下一次尝试时被复用
RESUMABLE_STAGES = ("uploaded", "transcribing", "exporting", "downloading")

# 终态
TERMINAL_STAGES = ("saved", "failed")


class TranscribeRunRepository:
    """transcribe_runs 表的访问层"""

    @staticmethod
    def create(
        *,
        asset_id: str,
        video_path: str,
        account_id: str,
        task_id: str | None = None,
    ) -> str:
        run_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO transcribe_runs
                    (run_id, asset_id, video_path, account_id, task_id, stage, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, 'queued', ?, ?)
                """,
                (run_id, asset_id, video_path, account_id, task_id, now, now),
            )
        return run_id

    @staticmethod
    def find_resumable(asset_id: str, account_id: str) -> dict[str, Any] | None:
        """查找该 asset 在该 account 上可以续做的 run。

        返回 stage 属于 RESUMABLE_STAGES 且 record_id/gen_record_id 已持久化的最近一条。
        """
        placeholders = ",".join(["?"] * len(RESUMABLE_STAGES))
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                f"""
                SELECT run_id, stage, record_id, gen_record_id, batch_id, export_task_id, export_url
                FROM transcribe_runs
                WHERE asset_id = ? AND account_id = ?
                  AND stage IN ({placeholders})
                  AND gen_record_id IS NOT NULL AND gen_record_id != ''
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (asset_id, account_id, *RESUMABLE_STAGES),
            ).fetchone()
        if row is None:
            return None
        return dict(row)

    @staticmethod
    def update_stage(
        run_id: str,
        stage: str,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """推进 stage，并可选地写入 record_id / gen_record_id / batch_id 等附加字段。"""
        extra = extra or {}
        allowed = {"record_id", "gen_record_id", "batch_id", "export_task_id", "export_url", "transcript_path"}
        set_clauses = ["stage = ?", "updated_at = ?"]
        params: list[Any] = [stage, datetime.now().isoformat()]
        for key in allowed:
            if key in extra and extra[key] is not None:
                set_clauses.append(f"{key} = ?")
                params.append(str(extra[key]))
        params.append(run_id)
        with get_db_connection() as conn:
            conn.execute(
                f"UPDATE transcribe_runs SET {', '.join(set_clauses)} WHERE run_id = ?",
                params,
            )

    @staticmethod
    def mark_saved(run_id: str, transcript_path: str) -> None:
        with get_db_connection() as conn:
            conn.execute(
                """
                UPDATE transcribe_runs
                SET stage = 'saved', transcript_path = ?, updated_at = ?, last_error = NULL, error_stage = NULL, error_type = NULL
                WHERE run_id = ?
                """,
                (transcript_path, datetime.now().isoformat(), run_id),
            )

    @staticmethod
    def mark_failed(
        run_id: str,
        error_stage: str,
        error_type: str,
        last_error: str,
    ) -> None:
        with get_db_connection() as conn:
            conn.execute(
                """
                UPDATE transcribe_runs
                SET stage = 'failed', error_stage = ?, error_type = ?, last_error = ?, updated_at = ?
                WHERE run_id = ?
                """,
                (error_stage, error_type, last_error[:2000], datetime.now().isoformat(), run_id),
            )

    @staticmethod
    def get(run_id: str) -> dict[str, Any] | None:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM transcribe_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        return dict(row) if row else None

    @staticmethod
    def find_saved_for_asset(asset_id: str) -> dict[str, Any] | None:
        """查询某个 asset 是否已经有成功落盘的 run。用于跨任务去重。"""
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT run_id, transcript_path, account_id
                FROM transcribe_runs
                WHERE asset_id = ? AND stage = 'saved'
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (asset_id,),
            ).fetchone()
        return dict(row) if row else None
