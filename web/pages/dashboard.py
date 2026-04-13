"""
仪表盘页面
"""

import streamlit as st
from pathlib import Path

from web.components.auth_status import render_auth_status_card
from web.components.stats_panel import render_stats_panel


def render_dashboard() -> None:
    """渲染仪表盘页面"""
    st.title("📊 仪表盘")

    # 认证状态
    render_auth_status_card()

    st.divider()

    # 统计面板
    render_stats_panel()

    st.divider()

    # 环境检测
    st.subheader("🔍 环境检测")
    if st.button("运行环境检测", type="primary"):
        with st.spinner("正在检测..."):
            passed, details = _run_env_check()
            if passed:
                st.success("✅ 环境检测通过")
            else:
                st.warning("⚠️ 部分检测项未通过，请查看下方详情")
            
            # 显示检测详情
            if details:
                st.divider()
                for name, info in details.items():
                    if info.get("ok"):
                        st.success(f"✅ {name}: {info.get('message', '')}")
                    else:
                        st.error(f"❌ {name}: {info.get('message', '')}")

    # 快速操作
    st.divider()
    st.subheader("⚡ 快速操作")
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("📋 查看关注列表", use_container_width=True):
            st.session_state.current_page = "👤 关注管理"
            st.rerun()

    with col2:
        if st.button("📥 开始下载", use_container_width=True):
            st.session_state.current_page = "📥 下载任务"
            st.rerun()

    with col3:
        if st.button("🎙️ 开始转写", use_container_width=True):
            st.session_state.current_page = "🎙️ 转写任务"
            st.rerun()


def _run_env_check() -> tuple:
    """运行环境检测
    
    Returns:
        tuple: (passed: bool, details: list[dict])
    """
    try:
        from media_tools.douyin.core.env_check import check_all

        passed, details = check_all()
        return passed, details
    except Exception as e:
        st.error(f"环境检测失败: {e}")
        return False, []
