"""Pipeline 流程编排器 V2 - 增强版

在原有基础上提供：
- 失败自动重试机制（可配置次数和指数退避延迟）
- 断点续传支持（状态持久化到 JSON 文件）
- 实时进度追踪（进度回调函数）
- 批量操作汇总报告（详细执行报告）
- 更好的错误处理（区分网络、配额、认证等错误类型）
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import sqlite3
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional, Callable, Awaitable, Any

from ..transcribe.flow import run_real_flow
from ..transcribe.runtime import get_export_config, ensure_dir, now_stamp
from ..transcribe.config import load_config as load_transcribe_config
from .config import PipelineConfig, load_pipeline_config

# 配置日志记录器
logger = logging.getLogger(__name__)

# 状态文件默认路径
DEFAULT_STATE_FILE = ".pipeline_state.json"


# --- helpers moved from orchestrator.py (V1) ---

def _clean_title_for_export(raw_title: str) -> str | None:
    """清洗标题用于导出文件名：去掉换行和 #话题标签"""
    main_part = raw_title.replace('<br>', '\n').split('\n')[0]
    if '#' in main_part:
        clean = main_part[:main_part.index('#')].strip()
    else:
        clean = main_part.strip()
    clean = re.sub(r'[<>:"/\\|?*]', '', clean).strip()
    if len(clean) > 50:
        clean = clean[:50]
    return clean if len(clean) > 2 else None


def _lookup_video_title(video_path: Path) -> str | None:
    """从数据库查询视频标题（通过文件名中的 aweme_id）"""
    aweme_matches = re.findall(r'\d{15,}', video_path.name)
    if not aweme_matches:
        return None

    aweme_id = aweme_matches[0]
    try:
        from media_tools.douyin.core.config_mgr import get_config as get_douyin_config
        db_path = get_douyin_config().get_db_path()
        with sqlite3.connect(str(db_path), timeout=15.0) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            cursor.execute("SELECT desc FROM video_metadata WHERE aweme_id = ?", (aweme_id,))
            row = cursor.fetchone()
            if not row or not row[0]:
                cursor.execute("SELECT title FROM media_assets WHERE asset_id = ?", (aweme_id,))
                row = cursor.fetchone()
            if row and row[0]:
                return _clean_title_for_export(row[0])
    except Exception as e:
        logger.warning(f"查询视频标题失败: {e}")

    return None


def _lookup_creator_folder(video_path: Path) -> str | None:
    """从数据库查询视频所属创作者昵称（用作转写子目录名）"""
    aweme_matches = re.findall(r'\d{15,}', video_path.name)
    if not aweme_matches:
        return None

    aweme_id = aweme_matches[0]
    try:
        from media_tools.douyin.core.config_mgr import get_config as get_douyin_config
        db_path = get_douyin_config().get_db_path()
        with sqlite3.connect(str(db_path), timeout=15.0) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            # media_assets.creator_uid -> creators.nickname
            cursor.execute("""
                SELECT c.nickname
                FROM media_assets ma
                JOIN creators c ON ma.creator_uid = c.uid
                WHERE ma.asset_id = ?
            """, (aweme_id,))
            row = cursor.fetchone()
            if row and row[0]:
                name = re.sub(r'[<>:"/\\|?*]', '', row[0]).strip()
                return name if name else None
            # Fallback: video_metadata.nickname
            cursor.execute("SELECT nickname FROM video_metadata WHERE aweme_id = ?", (aweme_id,))
            row = cursor.fetchone()
            if row and row[0]:
                name = re.sub(r'[<>:"/\\|?*]', '', row[0]).strip()
                return name if name else None
    except Exception as e:
        logger.warning(f"查询创作者信息失败: {e}")
    return None


class ErrorType(Enum):
    """错误类型枚举"""
    UNKNOWN = "unknown"
    NETWORK = "network"  # 网络错误
    QUOTA = "quota"  # 配额超限错误
    AUTH = "auth"  # 认证错误
    FILE_NOT_FOUND = "file_not_found"  # 文件不存在
    PERMISSION = "permission"  # 权限错误
    TIMEOUT = "timeout"  # 超时错误
    VALIDATION = "validation"  # 验证错误
    CANCELLED = "cancelled"  # 用户取消


def classify_error(error: Exception) -> ErrorType:
    """根据异常内容分类错误类型

    Args:
        error: 捕获的异常对象

    Returns:
        ErrorType: 分类后的错误类型
    """
    error_msg = str(error).lower()
    error_type = type(error).__name__.lower()

    # 认证错误
    if any(kw in error_msg for kw in ["auth", "unauthorized", "401", "403", "token", "credential", "permission denied"]):
        return ErrorType.AUTH

    # 网络错误
    if any(kw in error_msg for kw in ["connection", "network", "socket", "dns", "resolve", "unreachable"]):
        return ErrorType.NETWORK
    if any(kw in error_type for kw in ["connection", "timeout", "network"]):
        return ErrorType.NETWORK

    # 超时错误
    if any(kw in error_msg for kw in ["timeout", "timed out", "deadline"]):
        return ErrorType.TIMEOUT

    # 配额错误
    if any(kw in error_msg for kw in ["quota", "limit", "rate limit", "429", "exceeded", "too many"]):
        return ErrorType.QUOTA

    # 文件不存在
    if any(kw in error_msg for kw in ["not found", "no such file", "file not found", "does not exist", "找不到"]):
        return ErrorType.FILE_NOT_FOUND

    # 权限错误
    if any(kw in error_msg for kw in ["permission", "access denied", "forbidden"]):
        return ErrorType.PERMISSION

    # 验证错误
    if any(kw in error_msg for kw in ["invalid", "validation", "format", "parse"]):
        return ErrorType.VALIDATION

    return ErrorType.UNKNOWN


@dataclass
class RetryConfig:
    """重试配置

    Attributes:
        max_retries: 最大重试次数，默认3次
        base_delay: 基础延迟秒数，默认1秒（用于指数退避）
        max_delay: 最大延迟上限，默认60秒
        retryable_errors: 可重试的错误类型列表
    """
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
    """单个视频的处理状态

    Attributes:
        video_path: 视频文件路径
        status: 处理状态
        attempt: 当前尝试次数
        max_attempts: 最大尝试次数
        error_type: 错误类型（如果失败）
        error_message: 错误详情
        transcript_path: 转写结果路径（如果成功）
        started_at: 开始处理时间戳
        completed_at: 完成处理时间戳
        last_error_time: 最后一次错误发生时间
    """
    video_path: str
    status: str = "pending"  # pending, running, success, failed, cancelled
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
        """判断是否可以重试"""
        return self.status == "failed" and self.attempt < self.max_attempts

    @property
    def duration(self) -> float:
        """计算处理耗时（秒）"""
        if self.completed_at > 0 and self.started_at > 0:
            return self.completed_at - self.started_at
        return 0.0


@dataclass
class PipelineResultV2:
    """Pipeline 执行结果 V2

    Attributes:
        success: 是否成功
        video_path: 视频文件路径
        transcript_path: 转写结果路径（成功时）
        error: 错误信息（失败时）
        error_type: 错误类型
        attempts: 尝试次数
        duration: 总耗时（秒）
    """
    success: bool
    video_path: Path
    transcript_path: Optional[Path] = None
    error: Optional[str] = None
    error_type: ErrorType = ErrorType.UNKNOWN
    attempts: int = 1
    duration: float = 0.0

    def __str__(self) -> str:
        if self.success:
            return f"✅ 转写成功: {self.transcript_path} (耗时: {self.duration:.1f}s, 尝试: {self.attempts}次)"
        return f"❌ 转写失败 [{self.error_type.value}]: {self.error} (尝试: {self.attempts}次)"


@dataclass
class BatchReport:
    """批量执行汇总报告

    Attributes:
        total: 总视频数
        success: 成功数
        failed: 失败数
        skipped: 跳过数（已成功无需重试）
        total_duration: 总耗时（秒）
        avg_duration: 平均耗时（秒）
        results: 所有结果详情
        error_summary: 错误类型统计
        started_at: 开始时间
        completed_at: 完成时间
    """
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
        """转换为字典格式"""
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
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)

    def save_to_file(self, path: Path) -> None:
        """保存报告到文件

        Args:
            path: 报告文件路径
        """
        ensure_dir(path.parent)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_json())
        logger.info(f"报告已保存到: {path}")


class PipelineStateManager:
    """Pipeline 状态管理器 - 负责断点续传

    将每个视频的处理状态持久化到 JSON 文件，
    支持中断后从断点继续执行。
    """

    def __init__(self, state_file: Path | str = DEFAULT_STATE_FILE):
        """初始化状态管理器

        Args:
            state_file: 状态文件路径，默认 .pipeline_state.json
        """
        self.state_file = Path(state_file)
        self.states: dict[str, VideoState] = {}
        self._load()

    def _load(self) -> None:
        """从文件加载状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for path_str, state_data in data.items():
                    self.states[path_str] = VideoState(**state_data)
                logger.info(f"已加载状态文件: {self.state_file} ({len(self.states)} 条记录)")
            except Exception as e:
                logger.warning(f"加载状态文件失败，将创建新状态: {e}")
                self.states = {}
        else:
            logger.info(f"状态文件不存在，将创建新状态: {self.state_file}")

    def _save(self) -> None:
        """保存状态到文件"""
        try:
            data = {
                path: asdict(state)
                for path, state in self.states.items()
            }
            ensure_dir(self.state_file.parent)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"状态已保存到: {self.state_file}")
        except Exception as e:
            logger.error(f"保存状态文件失败: {e}")

    def get_state(self, video_path: Path) -> VideoState:
        """获取视频处理状态

        Args:
            video_path: 视频文件路径

        Returns:
            VideoState: 当前状态
        """
        key = str(video_path)
        if key not in self.states:
            self.states[key] = VideoState(video_path=str(video_path))
        return self.states[key]

    def update_state(
        self,
        video_path: Path,
        status: str,
        attempt: int = 0,
        max_attempts: int = 3,
        error_type: str = "",
        error_message: str = "",
        transcript_path: str = "",
    ) -> None:
        """更新视频处理状态

        Args:
            video_path: 视频文件路径
            status: 新状态 (pending/running/success/failed/cancelled)
            attempt: 当前尝试次数
            max_attempts: 最大尝试次数
            error_type: 错误类型
            error_message: 错误详情
            transcript_path: 转写结果路径
        """
        key = str(video_path)
        state = self.get_state(video_path)
        state.status = status
        state.attempt = attempt
        state.max_attempts = max_attempts

        if status == "running":
            state.started_at = time.time()
        elif status in ("success", "failed", "cancelled"):
            state.completed_at = time.time()
            if transcript_path:
                state.transcript_path = transcript_path
            if error_type:
                state.error_type = error_type
            if error_message:
                state.error_message = error_message
            if status == "failed":
                state.last_error_time = time.time()

        self._save()

    def get_pending_videos(self, video_paths: list[Path]) -> list[Path]:
        """获取待处理的视频列表（排除已成功且无需重试的）

        Args:
            video_paths: 所有视频路径列表

        Returns:
            list[Path]: 需要处理的视频路径列表
        """
        pending = []
        for path in video_paths:
            state = self.get_state(path)
            # 已成功或正在运行的跳过
            if state.status in ("success", "running"):
                continue
            pending.append(path)
        return pending

    def clear_completed(self) -> int:
        """清除已成功的状态记录

        Returns:
            int: 清除的记录数
        """
        before = len(self.states)
        self.states = {
            k: v for k, v in self.states.items()
            if v.status != "success"
        }
        self._save()
        return before - len(self.states)

    def reset_all(self) -> None:
        """重置所有状态"""
        self.states = {}
        self._save()
        logger.info("已重置所有状态")


# 进度回调类型定义
# on_progress(current: 当前完成数, total: 总数, video_path: 视频路径, status: 状态)
ProgressCallback = Callable[[int, int, Path, str], None]


class OrchestratorV2:
    """增强版 Pipeline 编排器

    支持：
    - 自动重试（指数退避）
    - 断点续传
    - 实时进度回调
    - 详细执行报告
    """

    def __init__(
        self,
        config: Optional[PipelineConfig] = None,
        auth_state_path: Optional[Path] = None,
        retry_config: Optional[RetryConfig] = None,
        state_file: Path | str = DEFAULT_STATE_FILE,
        on_progress: Optional[ProgressCallback] = None,
        creator_folder_override: Optional[str] = None,
    ):
        """初始化编排器

        Args:
            config: Pipeline 配置
            auth_state_path: 认证状态文件路径
            retry_config: 重试配置
            state_file: 状态持久化文件路径
            on_progress: 进度回调函数 on_progress(current, total, video_path, status)
            creator_folder_override: 强制指定转写文件子目录名（如"本地上传"）
        """
        self.config = config or load_pipeline_config()
        self.auth_state_path = auth_state_path
        self.retry_config = retry_config or RetryConfig()
        self.state_manager = PipelineStateManager(state_file)
        self.on_progress = on_progress
        self._creator_folder_override = creator_folder_override

        # 确定认证路径
        if self.auth_state_path is None:
            try:
                transcribe_config = load_transcribe_config()
                self.auth_state_path = transcribe_config.paths.auth_state_path
            except Exception as e:
                logger.warning(f"无法加载认证配置，将使用默认路径: {e}")

    def _fire_progress(
        self,
        current: int,
        total: int,
        video_path: Path,
        status: str,
    ) -> None:
        """触发进度回调

        Args:
            current: 当前完成数
            total: 总数
            video_path: 当前视频路径
            status: 状态描述
        """
        if self.on_progress:
            try:
                self.on_progress(current, total, video_path, status)
            except Exception as e:
                logger.warning(f"进度回调执行失败: {e}")

    async def _transcribe_single_video(
        self,
        video_path: Path,
    ) -> PipelineResultV2:
        """对单个视频执行转写（内部方法，不含重试）

        Args:
            video_path: 视频文件路径

        Returns:
            PipelineResultV2: 执行结果
        """
        start_time = time.time()

        # 检查文件是否存在
        if not video_path.exists():
            return PipelineResultV2(
                success=False,
                video_path=video_path,
                error=f"视频文件不存在: {video_path}",
                error_type=ErrorType.FILE_NOT_FOUND,
            )

        # 准备导出配置
        export_config = get_export_config(self.config.export_format)

        try:
            # 从数据库查询视频标题
            video_title = _lookup_video_title(video_path)

            # 确定创作者子目录
            creator_folder = self._creator_folder_override or _lookup_creator_folder(video_path) or "未分类"
            output_dir = str(Path(self.config.output_dir) / creator_folder)
            Path(output_dir).mkdir(parents=True, exist_ok=True)

            # 执行转写流程
            result = await run_real_flow(
                file_path=video_path,
                auth_state_path=self.auth_state_path,
                download_dir=output_dir,
                export_config=export_config,
                should_delete=self.config.delete_after_export,
                account_id=self.config.account_id,
                title=video_title,
            )

            # 可选：删除原视频
            if self.config.remove_video and not self.config.keep_original:
                video_path.unlink()
                logger.info(f"已删除原视频: {video_path}")

            duration = time.time() - start_time
            return PipelineResultV2(
                success=True,
                video_path=video_path,
                transcript_path=result.export_path,
                duration=duration,
            )

        except asyncio.CancelledError:
            duration = time.time() - start_time
            return PipelineResultV2(
                success=False,
                video_path=video_path,
                error="任务被取消",
                error_type=ErrorType.CANCELLED,
                duration=duration,
            )

        except Exception as e:
            duration = time.time() - start_time
            error_type = classify_error(e)
            logger.error(f"转写失败 [{error_type.value}]: {video_path} - {e}")
            return PipelineResultV2(
                success=False,
                video_path=video_path,
                error=str(e),
                error_type=error_type,
                duration=duration,
            )

    async def transcribe_with_retry(
        self,
        video_path: Path,
    ) -> PipelineResultV2:
        """对单个视频执行转写（带重试机制）

        Args:
            video_path: 视频文件路径

        Returns:
            PipelineResultV2: 最终执行结果
        """
        state = self.state_manager.get_state(video_path)

        # 如果已成功且无重试需求，直接返回缓存结果
        if state.status == "success" and state.transcript_path:
            logger.info(f"跳过已成功的视频: {video_path}")
            return PipelineResultV2(
                success=True,
                video_path=video_path,
                transcript_path=Path(state.transcript_path),
                attempts=state.attempt,
                duration=state.duration,
            )

        max_attempts = self.retry_config.max_retries + 1  # 首次 + 重试次数
        state.max_attempts = max_attempts
        total_attempts = 0

        for attempt in range(1, max_attempts + 1):
            total_attempts = attempt
            state.attempt = attempt

            # 标记为运行中
            self.state_manager.update_state(
                video_path,
                status="running",
                attempt=attempt,
                max_attempts=max_attempts,
            )
            self._fire_progress(
                0, 1, video_path,
                f"处理中 (尝试 {attempt}/{max_attempts})"
            )

            result = await self._transcribe_single_video(video_path)
            result.attempts = attempt

            if result.success:
                # 成功：更新状态
                self.state_manager.update_state(
                    video_path,
                    status="success",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    transcript_path=str(result.transcript_path) if result.transcript_path else "",
                )
                
                # 同步更新数据库
                try:
                    from media_tools.douyin.core.config_mgr import get_config
                    import sqlite3
                    import re
                    db_path = get_config().get_db_path()
                    with sqlite3.connect(db_path, timeout=15.0) as conn:
                        conn.execute("PRAGMA journal_mode=WAL;")
                        cursor = conn.cursor()
                        
                        if result.transcript_path:
                            try:
                                transcript_name = str(result.transcript_path.relative_to(Path(self.config.output_dir).resolve()))
                            except ValueError:
                                transcript_name = str(result.transcript_path.name)
                        else:
                            transcript_name = ""
                        aweme_matches = re.findall(r'\d{19}', video_path.name)
                        
                        if aweme_matches:
                            asset_id = aweme_matches[0]
                            cursor.execute("""
                                UPDATE media_assets 
                                SET transcript_path = ?, transcript_status = 'completed', update_time = CURRENT_TIMESTAMP
                                WHERE asset_id = ?
                            """, (
                                transcript_name, 
                                asset_id
                            ))
                        else:
                            cursor.execute("""
                                UPDATE media_assets 
                                SET transcript_path = ?, transcript_status = 'completed', update_time = CURRENT_TIMESTAMP
                                WHERE video_path LIKE ? OR title LIKE ?
                            """, (
                                transcript_name, 
                                f"%{video_path.name}%",
                                f"%{video_path.stem}%"
                            ))
                        conn.commit()
                except Exception as e:
                    logger.warning(f"更新 media_assets 转写状态失败: {e}")

                self._fire_progress(1, 1, video_path, "成功")
                logger.info(f"视频处理成功: {video_path} (尝试 {attempt} 次, 耗时 {result.duration:.1f}s)")
                return result

            # 失败：判断是否可重试
            if attempt < max_attempts and result.error_type in self.retry_config.retryable_errors:
                # 计算延迟（指数退避）
                delay = min(
                    self.retry_config.base_delay * (2 ** (attempt - 1)),
                    self.retry_config.max_delay,
                )
                logger.warning(
                    f"视频处理失败，将在 {delay:.1f}s 后重试 ({attempt}/{max_attempts}): "
                    f"[{result.error_type.value}] {result.error}"
                )
                self.state_manager.update_state(
                    video_path,
                    status="failed",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error_type=result.error_type.value,
                    error_message=result.error or "",
                )
                self._fire_progress(
                    0, 1, video_path,
                    f"失败，{delay:.0f}s 后重试 ({attempt}/{max_attempts})"
                )
                await asyncio.sleep(delay)
            else:
                # 不可重试或已达最大次数
                self.state_manager.update_state(
                    video_path,
                    status="failed",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    error_type=result.error_type.value,
                    error_message=result.error or "",
                )
                self._fire_progress(
                    0, 1, video_path,
                    f"失败 [{result.error_type.value}] (已达最大尝试次数)"
                )
                if attempt < max_attempts:
                    logger.error(
                        f"视频处理失败且不可重试 [{result.error_type.value}]: "
                        f"{video_path} - {result.error}"
                    )
                else:
                    logger.error(
                        f"视频处理失败，已达最大尝试次数 ({max_attempts}): "
                        f"{video_path} - {result.error}"
                    )
                return result

        # 理论上不会到这里，但加上保险
        return PipelineResultV2(
            success=False,
            video_path=video_path,
            error=f"已达最大尝试次数 ({max_attempts})",
            error_type=ErrorType.UNKNOWN,
            attempts=total_attempts,
        )

    async def transcribe_batch(
        self,
        video_paths: list[Path],
        resume: bool = True,
    ) -> BatchReport:
        """批量转写多个视频

        Args:
            video_paths: 视频文件路径列表
            resume: 是否启用断点续传（默认True）

        Returns:
            BatchReport: 批量执行报告
        """
        start_time = time.time()
        report = BatchReport(
            total=len(video_paths),
            started_at=start_time,
        )

        # 断点续传：过滤已成功/运行中的
        if resume:
            pending_paths = self.state_manager.get_pending_videos(video_paths)
            skipped_count = len(video_paths) - len(pending_paths)
            report.skipped = skipped_count
            logger.info(
                f"批量处理: 总计 {len(video_paths)} 个视频，"
                f"跳过 {skipped_count} 个（已成功/运行中），"
                f"待处理 {len(pending_paths)} 个"
            )
        else:
            pending_paths = list(video_paths)
            logger.info(f"批量处理: 共 {len(pending_paths)} 个视频（不启用断点续传）")

        # 如果无需处理任何视频
        if not pending_paths:
            report.completed_at = time.time()
            report.total_duration = report.completed_at - report.started_at
            logger.info("所有视频已处理完成，无需执行")
            return report

        # 并发控制
        semaphore = asyncio.Semaphore(self.config.concurrency)
        completed_count = 0
        total_pending = len(pending_paths)

        async def _process_with_semaphore(video_path: Path) -> PipelineResultV2:
            nonlocal completed_count
            async with semaphore:
                result = await self.transcribe_with_retry(video_path)
                completed_count += 1
                return result

        # 并发执行所有待处理视频
        tasks = [_process_with_semaphore(path) for path in pending_paths]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 汇总结果
        for result in results:
            if isinstance(result, Exception):
                # 异常情况 - 需要从tasks中找到对应的video_path
                error_type = classify_error(result)
                # 使用空Path并记录错误
                pipeline_result = PipelineResultV2(
                    success=False,
                    video_path=Path(""),
                    error=str(result),
                    error_type=error_type,
                )
                logger.error(f"任务执行异常: {result}")
            else:
                pipeline_result = result

            # 确保video_path不为空
            if not pipeline_result.video_path or not pipeline_result.video_path.exists():
                # 尝试从状态管理器中找到失败的记录
                for path_str, state in self.state_manager.states.items():
                    if state.status == "running":
                        pipeline_result.video_path = Path(path_str)
                        break

            # 添加到报告
            result_dict = {
                "video_path": str(pipeline_result.video_path),
                "success": pipeline_result.success,
                "transcript_path": str(pipeline_result.transcript_path) if pipeline_result.transcript_path else None,
                "error": pipeline_result.error,
                "error_type": pipeline_result.error_type.value,
                "attempts": pipeline_result.attempts,
                "duration": round(pipeline_result.duration, 2),
            }
            report.results.append(result_dict)

            if pipeline_result.success:
                report.success += 1
            else:
                report.failed += 1
                # 统计错误类型
                err_type = pipeline_result.error_type.value
                report.error_summary[err_type] = report.error_summary.get(err_type, 0) + 1

        # 计算总耗时
        end_time = time.time()
        report.completed_at = end_time
        report.total_duration = end_time - start_time
        processed = report.success + report.failed
        report.avg_duration = report.total_duration / processed if processed > 0 else 0.0

        logger.info(
            f"批量处理完成: 成功 {report.success}, 失败 {report.failed}, "
            f"跳过 {report.skipped}, 总耗时 {report.total_duration:.1f}s"
        )

        return report


def create_orchestrator(
    config: Optional[PipelineConfig] = None,
    auth_state_path: Optional[Path] = None,
    retry_config: Optional[RetryConfig] = None,
    state_file: Path | str = DEFAULT_STATE_FILE,
    on_progress: Optional[ProgressCallback] = None,
    creator_folder_override: Optional[str] = None,
) -> OrchestratorV2:
    """创建编排器实例的工厂函数

    Args:
        config: Pipeline 配置
        auth_state_path: 认证状态文件路径
        retry_config: 重试配置
        state_file: 状态持久化文件路径
        on_progress: 进度回调函数 on_progress(current, total, video_path, status)
        creator_folder_override: 强制指定转写文件子目录名（如"本地上传"）

    Returns:
        OrchestratorV2: 编排器实例

    Example:
        >>> orchestrator = create_orchestrator(
        ...     on_progress=lambda c, t, p, s: logger.info(f"[{c}/{t}] {p.name}: {s}")
        ... )
    """
    return OrchestratorV2(
        config=config,
        auth_state_path=auth_state_path,
        retry_config=retry_config,
        state_file=state_file,
        on_progress=on_progress,
        creator_folder_override=creator_folder_override,
    )


async def run_enhanced_pipeline(
    video_paths: list[Path],
    config: Optional[PipelineConfig] = None,
    auth_state_path: Optional[Path] = None,
    retry_config: Optional[RetryConfig] = None,
    state_file: Path | str = DEFAULT_STATE_FILE,
    on_progress: Optional[ProgressCallback] = None,
    resume: bool = True,
    report_path: Optional[Path] = None,
) -> BatchReport:
    """便捷函数：一键运行增强版 Pipeline

    Args:
        video_paths: 视频文件路径列表
        config: Pipeline 配置
        auth_state_path: 认证状态文件路径
        retry_config: 重试配置
        state_file: 状态持久化文件路径
        on_progress: 进度回调函数
        resume: 是否启用断点续传
        report_path: 报告保存路径（None则不保存）

    Returns:
        BatchReport: 执行报告

    Example:
        >>> report = await run_enhanced_pipeline(
        ...     video_paths=[Path("video1.mp4"), Path("video2.mp4")],
        ...     on_progress=lambda c, t, p, s: logger.info(f"{c}/{t}: {s}"),
        ...     report_path=Path("report.json"),
        ... )
        >>> logger.info(f"成功: {report.success}/{report.total}")
    """
    orchestrator = create_orchestrator(
        config=config,
        auth_state_path=auth_state_path,
        retry_config=retry_config,
        state_file=state_file,
        on_progress=on_progress,
    )
    report = await orchestrator.transcribe_batch(video_paths, resume=resume)

    # 可选：保存报告
    if report_path:
        report.save_to_file(report_path)

    return report


def print_enhanced_summary(report: BatchReport) -> None:
    """打印增强版执行摘要

    Args:
        report: 批量执行报告
    """
    logger.info("\n" + "=" * 60)
    logger.info("📊 Pipeline 增强版执行摘要")
    logger.info("=" * 60)
    logger.info(f"总计: {report.total}")
    logger.info(f"✅ 成功: {report.success}")
    logger.info(f"❌ 失败: {report.failed}")
    logger.info(f"⏭️  跳过: {report.skipped}")
    logger.info(f"⏱️  总耗时: {report.total_duration:.1f}s")
    if report.success + report.failed > 0:
        logger.info(f"📈 平均耗时: {report.avg_duration:.1f}s/视频")
    logger.info("=" * 60)

    if report.error_summary:
        logger.info("\n错误类型统计:")
        for err_type, count in report.error_summary.items():
            logger.info(f"  - [{err_type}]: {count} 次")

    if report.failed > 0:
        logger.info("\n失败详情:")
        for r in report.results:
            if not r["success"]:
                logger.info(f"  - {Path(r['video_path']).name}: [{r['error_type']}] {r['error']}")
                if r.get("attempts", 1) > 1:
                    logger.info(f"    (尝试了 {r['attempts']} 次)")

    logger.info("=" * 60)


def run_pipeline_batch(
    video_paths: list[Path],
    config: Optional[PipelineConfig] = None,
    auth_state_path: Optional[Path] = None,
) -> list:
    """同步包装器：批量转写（兼容原 orchestrator.py V1 接口）

    downloader.py 通过此函数在同步上下文中调用异步流水线。
    """
    report = asyncio.run(run_enhanced_pipeline(video_paths, config=config, auth_state_path=auth_state_path))

    class _Compat:
        """Lightweight shim: r.success / r.video_path / r.transcript_path / r.error"""
        def __init__(self, d: dict):
            self.success = d.get("success", False)
            self.video_path = Path(d["video_path"])
            self.transcript_path = Path(d["transcript_path"]) if d.get("transcript_path") else None
            self.error = d.get("error")

    return [_Compat(r) for r in report.results]
