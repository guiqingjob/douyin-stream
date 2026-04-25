"""Pipeline 数据模型"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional

from .error_types import ErrorType
from ..transcribe.runtime import ensure_dir

logger = logging.getLogger(__name__)


class AccountPool:
    """账号轮换池 - 按余额权重分配任务，余额多的分配更多"""

    def __init__(self, accounts: list[dict[str, Any]], balances: list[int] | None = None):
        self._accounts = accounts
        self._balances = balances or [0] * len(accounts)
        self._current = 0
        self._lock = asyncio.Lock()
        logger.info(f"初始化加权账号池，共 {len(accounts)} 个账号，总余额 {sum(self._balances)}")

    def get_account(self) -> dict[str, Any] | None:
        """按权重分配账号（余额多的分配更多）"""
        import random

        if not self._accounts:
            return None

        total = sum(self._balances)
        if total > 0:
            selected = random.choices(self._accounts, weights=self._balances, k=1)[0]
        else:
            account = self._accounts[self._current]
            self._current = (self._current + 1) % len(self._accounts)
            selected = account

        return selected

    async def acquire(self) -> dict[str, Any] | None:
        """异步获取一个账号（线程安全）"""
        async with self._lock:
            return self.get_account()

    def remaining(self) -> int:
        return len(self._accounts)


@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    retryable_errors: list[ErrorType] = field(default_factory=lambda: [
        ErrorType.NETWORK,
        ErrorType.TIMEOUT,
        ErrorType.QUOTA,
        ErrorType.UNKNOWN,
    ])


@dataclass
class VideoState:
    """单个视频的处理状态"""
    video_path: str
    status: str = "pending"
    attempt: int = 0
    max_attempts: int = 3
    error_type: str = ""
    error_message: str = ""
    transcript_path: str = ""
    started_at: float = 0.0
    completed_at: float = 0.0
    last_error_time: float = 0.0

    @property
    def can_retry(self) -> bool:
        return self.status == "failed" and self.attempt < self.max_attempts

    @property
    def duration(self) -> float:
        if self.completed_at > 0 and self.started_at > 0:
            return self.completed_at - self.started_at
        return 0.0


@dataclass
class PipelineResultV2:
    """Pipeline 执行结果 V2"""
    success: bool
    video_path: Path
    transcript_path: Optional[Path] = None
    error: Optional[str] = None
    error_type: ErrorType = ErrorType.UNKNOWN
    attempts: int = 1
    duration: float = 0.0

    def __str__(self) -> str:
        if self.success:
            return f"转写成功: {self.transcript_path} (耗时: {self.duration:.1f}s, 尝试: {self.attempts}次)"
        return f"转写失败 [{self.error_type.value}]: {self.error} (尝试: {self.attempts}次)"


@dataclass
class BatchReport:
    """批量执行汇总报告"""
    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    total_duration: float = 0.0
    avg_duration: float = 0.0
    results: list[dict] = field(default_factory=list)
    error_summary: dict[str, int] = field(default_factory=dict)
    started_at: float = 0.0
    completed_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "summary": {
                "total": self.total,
                "success": self.success,
                "failed": self.failed,
                "skipped": self.skipped,
                "total_duration_sec": round(self.total_duration, 2),
                "avg_duration_sec": round(self.avg_duration, 2),
                "started_at": self.started_at,
                "completed_at": self.completed_at,
            },
            "error_summary": self.error_summary,
            "results": self.results,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def save_to_file(self, path: Path) -> None:
        ensure_dir(path.parent)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())
        logger.info(f"报告已保存到: {path}")
