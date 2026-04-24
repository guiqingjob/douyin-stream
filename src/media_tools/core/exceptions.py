"""应用异常定义 - 统一的错误格式"""
from __future__ import annotations


class AppError(Exception):
    """应用异常基类 - 所有业务异常继承此类

    Attributes:
        code: 错误代码，用于前端识别错误类型
        message: 用户友好的错误消息
        details: 额外详情（可选）
    """

    def __init__(self, code: str, message: str, details: dict | None = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ConfigurationError(AppError):
    """配置错误"""

    def __init__(self, message: str, **kwargs):
        super().__init__("CONFIG_ERROR", message, kwargs)


class DownloadError(AppError):
    """下载错误"""

    def __init__(self, message: str, url: str | None = None, **kwargs):
        super().__init__("DOWNLOAD_ERROR", message, {"url": url, **kwargs})


class TranscribeError(AppError):
    """转写错误"""

    def __init__(self, message: str, file_path: str | None = None, **kwargs):
        super().__init__("TRANSCRIBE_ERROR", message, {"file_path": file_path, **kwargs})


class TaskCancelledError(AppError):
    """任务被取消"""

    def __init__(self, task_id: str):
        super().__init__("TASK_CANCELLED", f"任务 {task_id} 已取消", {"task_id": task_id})


class NotFoundError(AppError):
    """资源不存在"""

    def __init__(self, resource: str, identifier: str):
        super().__init__("NOT_FOUND", f"{resource} 不存在: {identifier}", {"resource": resource, "id": identifier})


class ValidationError(AppError):
    """参数校验失败"""

    def __init__(self, message: str, field: str | None = None):
        super().__init__("VALIDATION_ERROR", message, {"field": field})
