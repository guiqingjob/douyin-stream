"""Pipeline 错误类型分类"""
from __future__ import annotations

from enum import Enum


class ErrorType(Enum):
    """错误类型枚举"""
    UNKNOWN = "unknown"
    NETWORK = "network"
    QUOTA = "quota"
    AUTH = "auth"
    FILE_NOT_FOUND = "file_not_found"
    PERMISSION = "permission"
    TIMEOUT = "timeout"
    VALIDATION = "validation"
    CANCELLED = "cancelled"


def classify_error(error: Exception) -> ErrorType:
    """根据异常内容分类错误类型"""
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
