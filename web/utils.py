"""
Web 管理面板公共工具函数
"""

from datetime import datetime

import streamlit as st

_TASK_TYPE_LABELS = {
    "download": "单链接下载",
    "batch_download": "批量拉取素材",
    "transcribe": "单文件转写",
    "batch_transcribe": "批量转写",
}

_TASK_STATUS_LABELS = {
    "pending": "等待中",
    "running": "执行中",
    "success": "已完成",
    "failed": "失败",
}

_TASK_STATUS_WITH_ICON = {
    "pending": "⏳ 等待中",
    "running": "🔄 执行中",
    "success": "✅ 已完成",
    "failed": "❌ 失败",
}


def format_size(size_bytes: int) -> str:
    """格式化文件大小为人类可读格式"""
    if size_bytes > 1024 * 1024 * 1024:
        return f"{size_bytes / (1024**3):.2f} GB"
    if size_bytes > 1024 * 1024:
        return f"{size_bytes / (1024**2):.2f} MB"
    if size_bytes > 1024:
        return f"{size_bytes / 1024:.2f} KB"
    return f"{size_bytes} B"


def format_timestamp(value) -> str:
    """将 ISO 时间或时间戳格式化为统一展示字符串"""
    if not value:
        return "-"

    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S")

    if isinstance(value, str):
        try:
            cleaned = value.replace("Z", "+00:00")
            return datetime.fromisoformat(cleaned).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return value[:19]

    return str(value)


def get_task_type_label(task_type: str) -> str:
    """获取任务类型中文标签"""
    return _TASK_TYPE_LABELS.get(task_type, task_type or "未知")


def get_task_status_label(status: str, with_icon: bool = False) -> str:
    """获取任务状态中文标签"""
    if with_icon:
        return _TASK_STATUS_WITH_ICON.get(status, f"❓ {status or '未知'}")
    return _TASK_STATUS_LABELS.get(status, status or "未知")


def safe_json_display(data):
    """安全的 JSON 显示，处理不可序列化对象"""
    try:
        st.json(data)
    except TypeError as e:
        st.warning(f"JSON 序列化失败，显示为文本: {e}")
        st.code(str(data))
