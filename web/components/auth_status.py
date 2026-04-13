"""
认证状态卡片组件
"""

import streamlit as st

from web.constants import QWEN_AUTH_PATH
from web.utils import format_size

from media_tools.logger import get_logger
logger = get_logger('web')



def render_auth_status_card() -> None:
    """渲染认证状态卡片"""
    st.subheader("🔐 认证状态")

    col1, col2 = st.columns(2)

    with col1:
        douyin_auth = _check_douyin_auth()
        if douyin_auth:
            st.success("✅ 抖音已认证")
        else:
            st.error("❌ 抖音未认证")
            st.caption("请通过 CLI 运行: `python cli.py` → 11 → 2 扫码登录")

    with col2:
        qwen_auth = _check_qwen_auth()
        if qwen_auth:
            st.success("✅ Qwen 转写已认证")
        else:
            st.error("❌ Qwen 转写未认证")
            st.caption("请通过 CLI 运行: `python cli.py` → 9 扫码登录")


def _check_douyin_auth() -> bool:
    """检查抖音认证状态"""
    try:
        from media_tools.douyin.core.config_mgr import get_config

        config = get_config()
        return config.has_cookie()
    except Exception:
        logger.exception('发生异常')
        return False


def _check_qwen_auth() -> bool:
    """检查 Qwen 认证状态"""
    if QWEN_AUTH_PATH.exists():
        return QWEN_AUTH_PATH.stat().st_size > 1000  # 有效文件应大于1KB
    return False
