#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一日志系统 - 为整个项目提供日志记录功能

功能：
- 分级日志（DEBUG/INFO/WARNING/ERROR）
- 彩色终端输出
- 文件持久化
- 日志轮转（自动清理旧日志）
- 性能追踪
"""

import json
import logging
import os
import re
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional

from rich.console import Console
from rich.logging import RichHandler

console = Console()

# ANSI 颜色转义码正则（用于文件日志自动过滤颜色）
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


class StripAnsiFormatter(logging.Formatter):
    """文件日志 formatter：自动过滤 ANSI 颜色代码，避免日志文件出现 [92m 等转义码。"""

    def format(self, record: logging.LogRecord) -> str:
        s = super().format(record)
        return _ANSI_RE.sub("", s)


class JsonFormatter(logging.Formatter):
    """JSON 结构化日志 formatter，便于日志采集系统解析。"""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": _ANSI_RE.sub("", str(record.getMessage())),
        }
        if hasattr(record, "exc_info") and record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "stack_info") and record.stack_info:
            payload["stack"] = record.stack_info
        # 支持额外字段
        for key, value in record.__dict__.items():
            if key not in {
                "name", "msg", "args", "levelname", "levelno", "pathname",
                "filename", "module", "exc_info", "exc_text", "stack_info",
                "lineno", "funcName", "created", "msecs", "relativeCreated",
                "thread", "threadName", "processName", "process", "message",
                "asctime", "taskName",
            }:
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False, default=str)


class MediaLogger:
    """统一日志管理器"""

    def __init__(
        self,
        name: str = "media_tools",
        log_dir: Path = Path("logs"),
        level: int = logging.INFO,
        max_files: int = 10,
        max_age_days: int = 30,
        json_logs: bool = False,
    ):
        self.name = name
        self.log_dir = log_dir
        self.max_files = max_files
        self.max_age_days = max_age_days
        self.json_logs = json_logs

        # 确保日志目录存在
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 创建logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # 避免重复添加handler
        if not self.logger.handlers:
            self._setup_handlers()

    def _setup_handlers(self):
        """配置日志handler"""
        # 1. 终端输出（Rich）
        rich_handler = RichHandler(
            console=console,
            show_time=True,
            show_level=True,
            show_path=False,
            markup=True,
        )
        rich_handler.setLevel(logging.INFO)
        rich_handler.setFormatter(logging.Formatter(
            "%(message)s",
            datefmt="[%X]"
        ))
        self.logger.addHandler(rich_handler)

        # 2. 文件输出（过滤 ANSI 颜色代码）
        log_file = self.log_dir / f"media_tools_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(StripAnsiFormatter(
            "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        self.logger.addHandler(file_handler)

        # 3. 错误文件输出（过滤 ANSI 颜色代码）
        error_file = self.log_dir / f"error_{datetime.now().strftime('%Y%m%d')}.log"
        error_handler = logging.FileHandler(error_file, encoding="utf-8")
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(StripAnsiFormatter(
            "%(asctime)s [ERROR] %(name)s\n%(message)s\n%(exc_info)s\n"
        ))
        self.logger.addHandler(error_handler)

        # 4. JSON 结构化日志（可选，通过环境变量 MEDIA_TOOLS_JSON_LOGS=1 启用）
        if self.json_logs:
            json_file = self.log_dir / f"media_tools_{datetime.now().strftime('%Y%m%d')}.jsonl"
            json_handler = logging.FileHandler(json_file, encoding="utf-8")
            json_handler.setLevel(logging.DEBUG)
            json_handler.setFormatter(JsonFormatter())
            self.logger.addHandler(json_handler)

    def _cleanup_old_logs(self):
        """清理旧日志文件"""
        if not self.log_dir.exists():
            return

        cutoff_date = datetime.now() - timedelta(days=self.max_age_days)

        for log_file in self.log_dir.glob("*.log"):
            try:
                file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_mtime < cutoff_date:
                    log_file.unlink()
                    self.logger.info(f"清理旧日志: {log_file.name}")
            except (OSError, PermissionError) as e:
                self.logger.warning(f"清理日志失败: {e}")

    def _clean_msg(self, message: str) -> str:
        """清理消息中的 ANSI 颜色代码，避免和 RichHandler 的颜色叠加。"""
        if message is None:
            return ""
        return _ANSI_RE.sub("", message)

    def debug(self, message: str = "", *args, **kwargs):
        """DEBUG级别日志"""
        self.logger.debug(self._clean_msg(message), *args, **kwargs)

    def info(self, message: str = "", *args, **kwargs):
        """INFO级别日志"""
        self.logger.info(self._clean_msg(message), *args, **kwargs)

    def warning(self, message: str = "", *args, **kwargs):
        """WARNING级别日志"""
        self.logger.warning(self._clean_msg(message), *args, **kwargs)

    def error(self, message: str = "", *args, exc_info=False, **kwargs):
        """ERROR级别日志"""
        self.logger.error(self._clean_msg(message), *args, exc_info=exc_info, **kwargs)

    def critical(self, message: str = "", *args, **kwargs):
        """CRITICAL级别日志"""
        self.logger.critical(self._clean_msg(message), *args, **kwargs)

    def exception(self, message: str = "", *args, **kwargs):
        """异常日志（自动包含堆栈信息）"""
        self.logger.exception(self._clean_msg(message), *args, **kwargs)

    def log_operation(
        self,
        operation: str,
        status: str,
        details: str = "",
        duration: float = 0,
    ):
        """记录操作日志（格式化）

        Args:
            operation: 操作名称
            status: 状态 (success/failed/warning)
            details: 详细信息
            duration: 耗时（秒）
        """
        icon = {
            "success": "✅",
            "failed": "❌",
            "warning": "⚠️",
            "running": "🔄",
        }.get(status.lower(), "📝")

        msg = f"{icon} {operation}"
        if details:
            msg += f" - {details}"
        if duration > 0:
            msg += f" ({duration:.1f}s)"

        if status.lower() == "success":
            self.info(msg)
        elif status.lower() == "failed":
            self.error(msg)
        elif status.lower() == "warning":
            self.warning(msg)
        else:
            self.info(msg)


# 全局日志实例
_logger: Optional[MediaLogger] = None


def get_logger(name: str = "media_tools") -> MediaLogger:
    """获取全局日志实例"""
    global _logger
    if _logger is None:
        json_logs = os.environ.get("MEDIA_TOOLS_JSON_LOGS", "").lower() in ("1", "true", "yes")
        _logger = MediaLogger(name, json_logs=json_logs)
    return _logger


def init_logging(
    level: str = "INFO",
    log_dir: Path = Path("logs"),
    max_files: int = 10,
    max_age_days: int = 30,
) -> MediaLogger:
    """初始化日志系统

    Args:
        level: 日志级别 (DEBUG/INFO/WARNING/ERROR)
        log_dir: 日志目录
        max_files: 最大日志文件数
        max_age_days: 日志保留天数

    Returns:
        MediaLogger实例
    """
    global _logger

    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }

    json_logs = os.environ.get("MEDIA_TOOLS_JSON_LOGS", "").lower() in ("1", "true", "yes")
    _logger = MediaLogger(
        name="media_tools",
        log_dir=log_dir,
        level=level_map.get(level.upper(), logging.INFO),
        max_files=max_files,
        max_age_days=max_age_days,
        json_logs=json_logs,
    )

    _logger.info(f"日志系统初始化完成 (级别: {level}, JSON日志: {json_logs})")
    return _logger


def main():
    """测试日志系统"""
    import time

    # 初始化
    logger = init_logging(level="DEBUG")

    # 测试各级别日志
    logger.debug("这是一条DEBUG日志")
    logger.info("这是一条INFO日志")
    logger.warning("这是一条WARNING日志")
    logger.error("这是一条ERROR日志")

    # 测试操作日志
    logger.log_operation("下载视频", "success", "video_001.mp4", 2.5)
    logger.log_operation("转写视频", "failed", "配额不足", 1.2)
    logger.log_operation("检查更新", "warning", "网络延迟", 5.0)

    # 测试异常日志
    try:
        raise ValueError("测试异常")
    except ValueError as e:
        logger.exception("捕获到异常")

    print("\n✅ 日志系统测试完成！")
    print(f"📁 日志文件保存在: {logger.log_dir}")


if __name__ == "__main__":
    main()
