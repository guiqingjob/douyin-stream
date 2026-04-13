"""
Web 管理面板公共工具函数
"""

import streamlit as st


def format_size(size_bytes: int) -> str:
    """
    格式化文件大小为人类可读格式

    Args:
        size_bytes: 文件大小（字节）

    Returns:
        格式化后的字符串，如 "1.23 MB"
    """
    if size_bytes > 1024 * 1024 * 1024:
        return f"{size_bytes / (1024**3):.2f} GB"
    elif size_bytes > 1024 * 1024:
        return f"{size_bytes / (1024**2):.2f} MB"
    elif size_bytes > 1024:
        return f"{size_bytes / 1024:.2f} KB"
    else:
        return f"{size_bytes} B"


def safe_json_display(data):
    """
    安全的 JSON 显示，处理不可序列化对象

    Args:
        data: 要显示的数据
    """
    try:
        st.json(data)
    except TypeError as e:
        st.warning(f"JSON 序列化失败，显示为文本: {e}")
        st.code(str(data))
