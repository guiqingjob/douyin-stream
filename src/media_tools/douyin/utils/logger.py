#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结构化日志系统 - 支持 JSON 格式、日志轮转、多级别日志
"""

import json
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pathlib import Path


class StructuredFormatter(logging.Formatter):
    """结构化日志格式器 - 输出 JSON 格式"""

    def format(self, record):
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # 添加额外字段
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "video_id"):
            log_data["video_id"] = record.video_id
        if hasattr(record, "operation"):
            log_data["operation"] = record.operation
        if hasattr(record, "duration"):
            log_data["duration"] = record.duration

        return json.dumps(log_data, ensure_ascii=False)


class HumanReadableFormatter(logging.Formatter):
    """人类可读格式器 - 用于控制台输出"""

    def format(self, record):
        # 颜色映射
        colors = {
            "DEBUG": "\033[36m",    # 青色
            "INFO": "\033[32m",     # 绿色
            "WARNING": "\033[33m",  # 黄色
            "ERROR": "\033[31m",    # 红色
            "CRITICAL": "\033[35m", # 紫色
        }
        reset = "\033[0m"
        color = colors.get(record.levelname, "")

        level = f"{color}{record.levelname:<7}{reset}"
        message = record.getMessage()

        # 错误级别显示模块和行号
        if record.levelno >= logging.ERROR:
            timestamp = self.formatTime(record, self.datefmt) if hasattr(self, 'datefmt') else self.formatTime(record)
            return f"{timestamp} | {level} | {record.module}:{record.lineno} | {message}"

        timestamp = self.formatTime(record, self.datefmt) if hasattr(self, 'datefmt') else self.formatTime(record)
        return f"{timestamp} | {level} | {message}"


def setup_logger(
    name="DouyinDownloader",
    log_dir=None,
    console_level=logging.INFO,
    file_level=logging.DEBUG,
    max_bytes=10*1024*1024,  # 10MB
    backup_count=5,
    enable_json_file=False
):
    """
    设置结构化日志记录器

    Args:
        name: 日志名称
        log_dir: 日志文件目录，如果为 None 则只输出到控制台
        console_level: 控制台日志级别
        file_level: 文件日志级别
        max_bytes: 单个日志文件最大大小（字节）
        backup_count: 保留的日志文件数量
        enable_json_file: 是否额外输出 JSON 格式日志文件

    Returns:
        logging.Logger 实例
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)  #  Logger 本身接收所有级别
    logger.propagate = False

    # 控制台处理器 - 人类可读格式
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(HumanReadableFormatter(
        "%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(console_handler)

    # 文件日志处理器（如果指定了 log_dir）
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        # 普通日志文件 - 带轮转
        log_file = log_path / "cli.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(HumanReadableFormatter(
            "%(asctime)s | %(levelname)-7s | %(module)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
        logger.addHandler(file_handler)

        # JSON 结构化日志文件（可选）
        if enable_json_file:
            json_log_file = log_path / "cli.json.log"
            json_handler = RotatingFileHandler(
                json_log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8"
            )
            json_handler.setLevel(file_level)
            json_handler.setFormatter(StructuredFormatter())
            logger.addHandler(json_handler)

    return logger


# 全局单例
logger = setup_logger()

