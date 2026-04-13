"""
首页状态卡片组件
"""

import streamlit as st
from pathlib import Path

from web.constants import DOWNLOADS_DIR, TRANSCRIPTS_DIR
from web.utils import format_size


def render_home_status_cards() -> dict:
    """渲染首页状态卡片
    
    Returns:
        dict: 系统状态信息
    """
    status = {
        "cookie_ok": False,
        "qwen_ok": False,
        "env_ok": False,
        "storage_usage": "0 MB",
        "storage_total": 0,
    }
    
    # 检查 Cookie 状态
    try:
        from media_tools.douyin.core.config_mgr import ConfigManager
        cfg = ConfigManager()
        cookie = cfg.get("cookie", {})
        status["cookie_ok"] = bool(cookie and (cookie.get("auto_extract") or cookie.get("manual")))
    except Exception:
        pass
    
    # 检查 Qwen 认证
    qwen_auth = Path(__file__).parent.parent.parent / ".auth" / "qwen-storage-state.json"
    status["qwen_ok"] = qwen_auth.exists() and qwen_auth.stat().st_size > 1000
    
    # 检查环境
    try:
        from media_tools.douyin.core.env_check import check_all
        passed, _ = check_all()
        status["env_ok"] = passed
    except Exception:
        pass
    
    # 计算存储使用
    total_size = 0
    for d in [DOWNLOADS_DIR, TRANSCRIPTS_DIR]:
        if d.exists():
            try:
                total_size += sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
            except Exception:
                pass
    status["storage_usage"] = format_size(total_size)
    status["storage_total"] = total_size
    
    # 显示卡片
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if status["cookie_ok"]:
            st.success("🍪 Cookie\n已配置")
        else:
            st.warning("🍪 Cookie\n未配置")
    
    with col2:
        if status["qwen_ok"]:
            st.success("🎙️ Qwen\n已认证")
        else:
            st.warning("🎙️ Qwen\n未认证")
    
    with col3:
        st.info(f"📦 存储\n{status['storage_usage']}")
    
    with col4:
        if status["env_ok"]:
            st.success("✅ 环境\n通过")
        else:
            st.warning("⚠️ 环境\n未通过")
    
    return status
