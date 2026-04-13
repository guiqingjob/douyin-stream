"""
任务表格组件
"""

import streamlit as st

from web.components.task_queue import load_task_history
from web.components.ui_patterns import render_empty_state, render_summary_metrics, render_table_section
from web.utils import format_timestamp, get_task_status_label, get_task_type_label, safe_json_display


def render_task_table(limit: int = 10) -> None:
    """渲染任务历史表格"""
    history = load_task_history(limit=limit)

    if not history:
        render_empty_state("暂无任务历史。", "执行过下载或转写任务后，这里会自动显示最近记录。")
        return

    success_count = sum(1 for task in history if task.get("status") == "success")
    failed_count = sum(1 for task in history if task.get("status") == "failed")

    render_summary_metrics(
        [
            {"label": "最近任务", "value": len(history)},
            {"label": "成功", "value": success_count},
            {"label": "失败", "value": failed_count},
        ]
    )

    table_data = []
    for task in history:
        table_data.append(
            {
                "状态": get_task_status_label(task.get("status"), with_icon=True),
                "类型": get_task_type_label(task.get("task_type", "未知")),
                "说明": task.get("description", "")[:40] or "-",
                "结果": task.get("message", "")[:40] or "-",
                "完成时间": format_timestamp(task.get("completed_at") or task.get("updated_at")),
            }
        )

    render_table_section(
        table_data,
        empty_message="当前没有可展示的任务记录。",
        hint="如需查看更多细节，可展开完整历史查看原始任务信息。",
    )

    if st.button("📜 查看完整历史", key="view_full_history"):
        _render_full_history(history)


def _render_full_history(history: list) -> None:
    """显示完整任务历史"""
    st.divider()
    st.subheader("完整任务历史")

    for i, task in enumerate(history):
        task_id = task.get("task_id", "未知")[:8]
        task_type = get_task_type_label(task.get("task_type", "未知"))
        status = task.get("status", "unknown")
        status_text = get_task_status_label(status, with_icon=True)
        message = task.get("message", "")
        completed_at = format_timestamp(task.get("completed_at") or task.get("updated_at"))

        st.markdown(f"**{status_text} [{task_type}]**  ")
        st.caption(f"任务 ID: {task_id} | 完成时间: {completed_at}")
        if message:
            st.write(message)

        if st.button(f"查看详情 {i}", key=f"history_detail_{i}"):
            with st.expander("完整任务信息", expanded=True):
                safe_json_display(task)

        if i < len(history) - 1:
            st.divider()
