"""
任务表格组件
"""

import streamlit as st
from web.components.task_queue import load_task_history
from web.utils import safe_json_display


def render_task_table(limit: int = 10) -> None:
    """渲染任务历史表格
    
    Args:
        limit: 显示最近 N 条记录
    """
    history = load_task_history(limit=limit)
    
    if not history:
        st.info("暂无任务历史")
        return
    
    # 表格数据
    table_data = []
    for task in history:
        table_data.append({
            "状态": _get_status_icon(task.get("status")),
            "类型": task.get("task_type", "未知"),
            "描述": task.get("description", "")[:30],
            "进度": f"{task.get('progress', 0)*100:.0f}%",
            "完成时间": task.get("completed_at", "")[:19] if task.get("completed_at") else "-",
        })
    
    st.dataframe(
        table_data,
        use_container_width=True,
        hide_index=True,
    )
    
    # 显示详情按钮
    if st.button("📜 查看完整历史", key="view_full_history"):
        _render_full_history(history)


def _get_status_icon(status: str) -> str:
    """获取状态图标"""
    icons = {
        "success": "✅",
        "failed": "❌",
        "running": "🔄",
        "pending": "⏳",
    }
    return icons.get(status, "❓")


def _render_full_history(history: list) -> None:
    """显示完整任务历史"""
    st.divider()
    st.subheader("完整任务历史")
    
    for i, task in enumerate(history):
        task_id = task.get("task_id", "未知")[:8]
        task_type = task.get("task_type", "未知")
        status = task.get("status", "unknown")
        message = task.get("message", "")
        
        if status == "success":
            st.success(f"✅ [{task_type}] {message} (ID: {task_id})")
        elif status == "failed":
            st.error(f"❌ [{task_type}] {message} (ID: {task_id})")
        else:
            st.info(f"⏳ [{task_type}] {message} (ID: {task_id})")
        
        # 显示详情
        if st.button(f"查看详情 {i}", key=f"history_detail_{i}"):
            with st.expander("完整任务信息"):
                safe_json_display(task)
        
        if i < len(history) - 1:
            st.divider()
