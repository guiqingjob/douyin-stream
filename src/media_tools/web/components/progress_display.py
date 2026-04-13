"""
进度显示组件
"""

import streamlit as st

from media_tools.web.components.task_queue import cancel_task, clear_task_state, load_task_state
from media_tools.web.components.ui_patterns import render_empty_state, render_summary_metrics, render_status_badge
from media_tools.web.utils import get_task_status_label, get_task_type_label, safe_json_display

from media_tools.logger import get_logger
logger = get_logger('web')



def render_task_progress(empty_message: str = "当前没有正在执行的任务") -> bool:
    """渲染当前任务进度

    Args:
        empty_message: 无任务时显示的文案

    Returns:
        bool: 当前是否存在处于 pending/running 状态的任务
    """
    state = load_task_state()
    if state is None:
        render_empty_state(empty_message, icon="🛌")
        return False

    task_type = state.get("task_type", "未知")
    status = state.get("status", "pending")
    progress = state.get("progress", 0.0)
    message = state.get("message", "")
    description = state.get("description", "")

    render_summary_metrics(
        [
            {"label": "任务类型", "value": get_task_type_label(task_type)},
            {"label": "当前状态", "value": get_task_status_label(status)},
            {"label": "当前进度", "value": f"{progress * 100:.0f}%"},
        ]
    )

    if description:
        st.caption(f"任务说明：{description}")

    st.progress(progress)

    if status == "pending":
        st.warning(f"⏳ {message}")
        return True

    if status == "running":
        st.info(f"🔄 {message}")
        if st.button("🛑 取消当前任务", type="secondary", key="cancel_task_btn"):
            cancel_task()
            st.warning("已发送取消信号，任务正在停止...")
            st.rerun()
        return True

    if status == "success":
        st.success(f"✅ {message}")
        if state.get("result"):
            _display_task_result(state["result"])
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🧹 清除状态", key="clear_success_state_btn"):
                clear_task_state()
                st.rerun()
        return False

    if status == "failed":
        st.error(f"❌ {message}")
        if st.button("🧹 清除状态", key="clear_failed_state_btn"):
            clear_task_state()
            st.rerun()
        return False

    return False


def _display_task_result(result) -> None:
    """显示任务结果，处理批量操作的统计报告"""
    if isinstance(result, dict) and "success_count" in result and "failed_count" in result:
        total = result.get("total_files", result.get("total_users", 0))
        success = result.get("success_count", 0)
        failed = result.get("failed_count", 0)

        render_summary_metrics(
            [
                {"label": "总计", "value": total},
                {"label": "成功", "value": success, "delta": None if total == 0 else f"{(success / total) * 100:.1f}%"},
                {"label": "失败", "value": failed, "delta": None if total == 0 else f"-{(failed / total) * 100:.1f}%"},
            ]
        )

        if success > 0 and success <= 20:
            with st.expander("查看成功列表"):
                for item in result.get("success_list", []):
                    st.success(f"✅ {item}")

        if failed > 0:
            with st.expander(f"查看 {failed} 个失败项详情"):
                for item in result.get("failed_list", []):
                    if isinstance(item, dict):
                        name = item.get("user", item.get("file", "未知"))
                        error = item.get("error", "未知错误")
                        st.warning(f"**{name}**: {error}")
                    else:
                        st.warning(str(item))
        return

    safe_json_display(result)


def render_task_history() -> None:
    """渲染任务历史页面"""
    from media_tools.web.components.task_table import render_task_table

    st.subheader("📜 任务历史")
    render_task_table(limit=20)
