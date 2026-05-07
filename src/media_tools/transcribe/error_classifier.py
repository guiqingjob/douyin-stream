from __future__ import annotations
"""错误分类模块 - 提供友好的错误消息和操作建议"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ErrorInfo:
    message: str
    suggestion: str
    retryable: bool
    error_code: Optional[str] = None


class TranscribeError(RuntimeError):
    """携带完整错误上下文的转写异常，供上层做精准重试/账号切换决策"""

    def __init__(self, error_info: ErrorInfo, detail: str = ""):
        self.error_info = error_info
        detail_suffix = f": {detail}" if detail else ""
        super().__init__(f"{error_info.message}{detail_suffix}")


class TranscribeErrorClassifier:
    _error_mapping = {
        "40": ErrorInfo(
            message="转写失败：服务暂时不可用",
            suggestion="请稍后重试，或切换其他账号",
            retryable=True,
            error_code="SERVICE_UNAVAILABLE"
        ),
        "41": ErrorInfo(
            message="转写失败：视频内容无法识别",
            suggestion="请检查视频文件是否损坏或格式不支持",
            retryable=False,
            error_code="UNSUPPORTED_FORMAT"
        ),
        "network": ErrorInfo(
            message="网络连接失败",
            suggestion="请检查网络连接后重试",
            retryable=True,
            error_code="NETWORK_ERROR"
        ),
        "timeout": ErrorInfo(
            message="请求超时",
            suggestion="网络不稳定，请稍后重试",
            retryable=True,
            error_code="TIMEOUT"
        ),
        "auth": ErrorInfo(
            message="账号权限不足",
            suggestion="请更新 Cookie 或切换账号",
            retryable=True,
            error_code="AUTH_ERROR"
        ),
        "quota": ErrorInfo(
            message="API 配额不足",
            suggestion="账号额度已用完，请添加新账号",
            retryable=False,
            error_code="QUOTA_EXCEEDED"
        ),
        "rate_limit": ErrorInfo(
            message="触发频率限制",
            suggestion="请求太频繁，请稍后重试",
            retryable=True,
            error_code="RATE_LIMITED"
        ),
        "file_not_found": ErrorInfo(
            message="资源不存在",
            suggestion="视频可能已被删除或链接失效",
            retryable=False,
            error_code="NOT_FOUND"
        ),
        "disk_full": ErrorInfo(
            message="磁盘空间不足",
            suggestion="请清理磁盘空间后重试",
            retryable=False,
            error_code="DISK_FULL"
        ),
    }
    
    @classmethod
    def classify(cls, error_message: str) -> ErrorInfo:
        error_msg = str(error_message).lower()
        
        for code, info in cls._error_mapping.items():
            if code in error_msg or (info.error_code and info.error_code.lower() in error_msg):
                return info
        
        if "network" in error_msg or "connection" in error_msg:
            return cls._error_mapping["network"]
        if "timeout" in error_msg:
            return cls._error_mapping["timeout"]
        if "auth" in error_msg or "cookie" in error_msg or "permission" in error_msg:
            return cls._error_mapping["auth"]
        if "quota" in error_msg or ("limit" in error_msg and "exceed" in error_msg):
            return cls._error_mapping["quota"]
        if "rate" in error_msg or "frequency" in error_msg:
            return cls._error_mapping["rate_limit"]
        if "not found" in error_msg or "不存在" in error_msg:
            return cls._error_mapping["file_not_found"]
        if "disk" in error_msg or "space" in error_msg:
            return cls._error_mapping["disk_full"]
        
        return ErrorInfo(
            message=f"发生未知错误: {error_message[:50]}",
            suggestion="请联系开发者",
            retryable=False,
            error_code="UNKNOWN"
        )
