"""
认证状态卡片组件
"""

import streamlit as st

from media_tools.web.constants import QWEN_AUTH_PATH
from media_tools.web.utils import format_size

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
            st.caption("可在「账号与配额 -> 认证配置」中粘贴 Cookie")

    with col2:
        qwen_auth = _check_qwen_auth()
        if qwen_auth:
            st.success("✅ Qwen 转写已认证")
        else:
            st.error("❌ Qwen 转写未认证")
            st.caption("可在「账号与配额 -> 认证配置」中粘贴 Cookie")


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
    try:
        from media_tools.douyin.core.config_mgr import get_config
        import sqlite3
        
        cfg = get_config()
        with sqlite3.connect(cfg.get_db_path()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM auth_credentials WHERE platform = 'qwen' AND is_valid = 1")
            return cursor.fetchone() is not None
    except Exception:
        # Fallback
        if QWEN_AUTH_PATH.exists():
            return QWEN_AUTH_PATH.stat().st_size > 50
        return False
