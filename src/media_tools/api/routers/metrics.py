"""轻量 metrics 端点：暴露任务队列、WebSocket、后台任务、DB 连接等关键指标。

不引入 Prometheus 依赖；返回 JSON 格式，方便 ops 用 curl 或简单脚本采集。
"""
from __future__ import annotations

import logging
import sqlite3
import time

from fastapi import APIRouter

from media_tools.api.websocket_manager import manager as ws_manager
from media_tools.core import background
from media_tools.db.core import DBConnection, get_db_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])

_KNOWN_TASK_STATUSES = ("PENDING", "RUNNING", "PAUSED", "COMPLETED", "FAILED", "CANCELLED")
_PROCESS_START_TIME = time.monotonic()


def _collect_task_counts() -> dict[str, int]:
    counts: dict[str, int] = {s: 0 for s in _KNOWN_TASK_STATUSES}
    try:
        with get_db_connection() as conn:
            conn.row_factory = sqlite3.Row
            for row in conn.execute("SELECT status, COUNT(*) AS c FROM task_queue GROUP BY status"):
                status = str(row["status"] or "").upper()
                if status:
                    counts[status] = counts.get(status, 0) + int(row["c"])
    except (sqlite3.Error, OSError) as e:
        logger.warning(f"metrics: read task counts failed: {e}")
    counts["total"] = sum(v for k, v in counts.items() if k != "total")
    counts["active"] = counts.get("PENDING", 0) + counts.get("RUNNING", 0) + counts.get("PAUSED", 0)
    return counts


@router.get("/")
def get_metrics():
    return {
        "uptime_seconds": int(time.monotonic() - _PROCESS_START_TIME),
        "tasks": _collect_task_counts(),
        "websocket": ws_manager.get_stats(),
        "background_tasks": {
            "active": background.active_count(),
            "total": background.total_count(),
        },
        "db_connections": DBConnection.get_stats(),
    }
