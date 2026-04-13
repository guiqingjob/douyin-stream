"""
首页 - 总览仪表盘
"""

import streamlit as st
from pathlib import Path

from web.components.home_cards import render_home_status_cards
from web.components.task_table import render_task_table
from web.components.storage_chart import render_storage_chart


def render_home() -> None:
    """渲染首页"""
    st.title("🏠 首页")
    
    # 欢迎信息
    status = render_home_status_cards()
    
    # 根据系统状态显示不同提示
    _render_welcome_message(status)
    
    st.divider()
    
    # 快速操作区
    _render_quick_actions()
    
    st.divider()
    
    # 最近任务历史
    st.subheader("📊 最近任务历史")
    render_task_table(limit=5)
    
    st.divider()
    
    # 存储使用
    render_storage_chart()


def _render_welcome_message(status: dict) -> None:
    """根据系统状态显示欢迎信息"""
    all_ok = status["cookie_ok"] and status["qwen_ok"] and status["env_ok"]
    
    if all_ok:
        st.success("👋 欢迎回来！系统运行正常，所有服务已就绪。")
    else:
        missing = []
        if not status["cookie_ok"]:
            missing.append("Cookie 未配置")
        if not status["qwen_ok"]:
            missing.append("Qwen 未认证")
        if not status["env_ok"]:
            missing.append("环境检测未通过")
        
        st.warning(f"⚠️ 欢迎使用 Media Tools！以下项目需要配置：{', '.join(missing)}")
        st.info("💡 提示：前往 **系统设置** 页面完成配置。")


def _render_quick_actions() -> None:
    """渲染快速操作区"""
    st.subheader("⚡ 快速操作")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("📥 下载视频", use_container_width=True, type="primary"):
            st.session_state.current_page = "📥 下载中心"
            st.rerun()
    
    with col2:
        if st.button("🎙️ 转写文件", use_container_width=True, type="primary"):
            st.session_state.current_page = "🎙️ 转写中心"
            st.rerun()
    
    with col3:
        if st.button("👥 关注管理", use_container_width=True):
            st.session_state.current_page = "👥 关注管理"
            st.rerun()
    
    with col4:
        if st.button("⚙️ 系统设置", use_container_width=True):
            st.session_state.current_page = "⚙️ 系统设置"
            st.rerun()
