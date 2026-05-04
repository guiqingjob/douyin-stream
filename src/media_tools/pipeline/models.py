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
    """账号轮换池 - 按余额权重分配任务，余额多的分配更多

    每个账号可同时处理多个任务（per-account 并发上限），
    按余额加权选择账号：余额高的账号被分配更多并发任务。
    """

    # 每个账号默认最大并发数
    DEFAULT_MAX_CONCURRENT = 10

    def __init__(
        self,
        accounts: list[dict[str, Any]],
        balances: list[int] | None = None,
        max_concurrent_per_account: int | None = None,
    ):
        self._accounts = accounts
        self._balances = balances or [0] * len(accounts)
        self._current = 0
        self._lock = asyncio.Lock()
        self._max_concurrent = max_concurrent_per_account or self.DEFAULT_MAX_CONCURRENT
        # 每个 account_id 当前正在处理的任务数
        self._active_count: dict[str, int] = {}
        logger.info(
            f"初始化加权账号池，共 {len(accounts)} 个账号，"
            f"总余额 {sum(self._balances)}，每账号最大并发 {self._max_concurrent}"
        )

    def _pick_account(self) -> dict[str, Any] | None:
        """内部方法：按权重选一个有空闲槽位的账号（调用方需持锁）"""
        import random

        if not self._accounts:
            return None

        # 筛选有空闲槽位的账号
        available = [
            (i, a) for i, a in enumerate(self._accounts)
            if self._active_count.get(str(a.get("account_id", "")), 0) < self._max_concurrent
        ]

        if not available:
            return None

        indices, accounts = zip(*available)
        balances = [self._balances[i] for i in indices]
        total = sum(balances)

        if total > 0:
            safe_balances = [max(b, 1) for b in balances]
            selected = random.choices(accounts, weights=safe_balances, k=1)[0]
        else:
            selected = accounts[self._current % len(accounts)]
            self._current = (self._current + 1) % len(accounts)

        return selected

    async def acquire(self, preferred_account_id: str | None = None) -> dict[str, Any] | None:
        """获取一个有空闲槽位的账号（并发安全）

        每个账号可同时处理 max_concurrent 个任务。
        全部满载时阻塞等待，直到有槽位释放。
        """
        while True:
            async with self._lock:
                selected = None
                if preferred_account_id:
                    for account in self._accounts:
                        account_id = str(account.get("account_id", ""))
                        if account_id == preferred_account_id and self._active_count.get(account_id, 0) < self._max_concurrent:
                            selected = account
                            break
                else:
                    selected = self._pick_account()

                if selected is not None:
                    account_id = str(selected.get("account_id", ""))
                    self._active_count[account_id] = self._active_count.get(account_id, 0) + 1
                    return selected

            await asyncio.sleep(1)

    def release(self, account_id: str) -> None:
        """释放一个并发槽位"""
        cur = self._active_count.get(account_id, 0)
        if cur > 1:
            self._active_count[account_id] = cur - 1
        else:
            self._active_count.pop(account_id, None)

    def remaining(self) -> int:
        """还有空闲槽位的账号数"""
        return sum(
            1 for a in self._accounts
            if self._active_count.get(str(a.get("account_id", "")), 0) < self._max_concurrent
        )


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
    account_id: str | None = None

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
