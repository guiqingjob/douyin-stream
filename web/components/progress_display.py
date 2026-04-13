"""
进度显示组件
"""

import time
import streamlit as st

from web.components.task_queue import load_task_state, clear_task_state, cancel_task, is_task_cancelled
from web.utils import safe_json_display


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
        # 添加取消按钮
        if st.button("🛑 取消任务", type="secondary", key="cancel_task_btn"):
            cancel_task()
            st.warning("已发送取消信号，任务正在停止...")
            st.rerun()
    elif status == "success":
        st.success(f"✅ {message}")
        if state.get("result"):
            _display_task_result(state["result"])
        clear_task_state()
        return True
    elif status == "failed":
        st.error(f"❌ {message}")
        clear_task_state()
        return True

    return False


def _display_task_result(result) -> None:
    """显示任务结果，处理批量操作的统计报告"""
    # 检查是否是批量操作的统计报告
    if isinstance(result, dict) and "success_count" in result and "failed_count" in result:
        total = result.get("total_files", result.get("total_users", 0))
        success = result.get("success_count", 0)
        failed = result.get("failed_count", 0)

        # 显示统计摘要
        cols = st.columns(3)
        cols[0].metric("总计", total)
        cols[1].metric("成功", success, delta=None if success == 0 else f"{success/total*100:.1f}%")
        cols[2].metric("失败", failed, delta=None if failed == 0 else f"-{failed/total*100:.1f}%")

        # 显示失败详情
        if failed > 0:
            with st.expander(f"查看 {failed} 个失败项详情"):
                for item in result.get("failed_list", []):
                    if isinstance(item, dict):
                        name = item.get("user", item.get("file", "未知"))
                        error = item.get("error", "未知错误")
                        st.warning(f"**{name}**: {error}")
                    else:
                        st.warning(str(item))

        # 显示成功列表（仅当数量较少时）
        if success > 0 and success <= 20:
            with st.expander("查看成功列表"):
                success_list = result.get("success_list", [])
                for item in success_list:
                    st.success(f"✅ {item}")
    else:
        # 普通结果，使用安全 JSON 显示
        safe_json_display(result)
