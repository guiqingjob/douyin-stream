"""
进度显示组件
"""

import time
import streamlit as st
from web.components.task_queue import load_task_state, clear_task_state


def render_task_progress(refresh_interval: float = 2.0) -> bool:
    """
    渲染任务进度条

    Args:
        refresh_interval: 刷新间隔（秒）

    Returns:
        是否任务已完成
    """
    state = load_task_state()
    if state is None:
        st.info("当前无运行中的任务")
        return False

    task_type = state.get("task_type", "未知")
    status = state.get("status", "pending")
    progress = state.get("progress", 0.0)
    message = state.get("message", "")

    st.info(f"📌 任务类型: {task_type} | 状态: {status}")

    # 进度条
    progress_bar = st.progress(progress)

    # 状态消息
    if status == "pending":
        st.warning(f"⏳ {message}")
    elif status == "running":
        st.info(f"🔄 {message}")
    elif status == "success":
        st.success(f"✅ {message}")
        if state.get("result"):
            st.json(state["result"])
        clear_task_state()
        return True
    elif status == "failed":
        st.error(f"❌ {message}")
        clear_task_state()
        return True

    return False
