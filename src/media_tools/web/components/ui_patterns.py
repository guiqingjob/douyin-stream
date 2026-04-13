"""
Web 通用 UI 模式组件
"""

from typing import Iterable, Sequence

import streamlit as st

from media_tools.logger import get_logger
logger = get_logger('web')


def render_page_header(title: str, subtitle: str | None = None, tag: str | None = None) -> None:
    tag_html = f'<span class="mt-tag">{tag}</span>' if tag else ""
    subtitle_html = f'<p class="mt-page-subtitle">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f"""
<div class="mt-page-header">
  <div class="mt-page-title">{title}{tag_html}</div>
  {subtitle_html}
</div>
""",
        unsafe_allow_html=True,
    )



def render_summary_metrics(items: Sequence[dict]) -> None:
    """渲染统一摘要指标区

    每个 item 支持：
    - value: 指标值
    - delta: 可选变化文案
    """
    if not items:
        return

    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        col.metric(
            item.get("label", "-"),
            item.get("value", "-"),
            delta=item.get("delta"),
            border=True,
        )


def render_highlight_card(title: str, main_text: str, meta_lines: Iterable[str] | None = None) -> None:
    """渲染统一的结果高亮卡片"""
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.write(main_text or "-")
        for line in meta_lines or []:
            if line:
                st.caption(line)


def render_empty_state(message: str, hint: str | None = None, icon: str = "✨") -> None:
    """渲染带图标/插画占位的统一空状态"""
    st.markdown(
        f"""
        <div style="text-align: center; padding: 3rem 1rem; background: var(--mt-bg0); border-radius: 8px; border: 1px dashed var(--mt-border2); margin: 1rem 0;">
            <div style="font-size: 3rem; margin-bottom: 1rem; opacity: 0.6;">{icon}</div>
            <h4 style="margin: 0 0 0.5rem 0; color: var(--mt-text); font-weight: 500;">{message}</h4>
            {f'<p style="margin: 0; color: var(--mt-text2); font-size: 14px;">{hint}</p>' if hint else ''}
        </div>
        """,
        unsafe_allow_html=True
    )


def render_cta_section(title: str, description: str, button_text: str, button_key: str, on_click=None) -> bool:
    """渲染统一的 CTA (Call To Action) 引导区"""
    with st.container(border=True):
        col1, col2 = st.columns([3, 1], gap="large", vertical_alignment="center")
        with col1:
            st.markdown(f"#### {title}")
            st.caption(description)
        with col2:
            return st.button(button_text, type="primary", use_container_width=True, key=button_key, on_click=on_click)


def render_danger_zone(title: str, description: str, button_text: str, button_key: str) -> bool:
    """渲染危险操作区 (Danger Zone)，带二次确认逻辑"""
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.caption(description)
        
        # 使用 session_state 管理二次确认状态
        confirm_key = f"confirm_{button_key}"
        if confirm_key not in st.session_state:
            st.session_state[confirm_key] = False
            
        if not st.session_state[confirm_key]:
            if st.button(button_text, key=f"init_{button_key}", help="该操作可能无法撤销"):
                st.session_state[confirm_key] = True
                st.rerun()
            return False
        else:
            st.warning("⚠️ 确认执行该操作？此操作不可逆。")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("取消", key=f"cancel_{button_key}", use_container_width=True):
                    st.session_state[confirm_key] = False
                    st.rerun()
            with col2:
                if st.button("确认执行", type="primary", key=f"exec_{button_key}", use_container_width=True):
                    st.session_state[confirm_key] = False
                    return True
            return False


def render_status_badge(status: str, label: str) -> None:
    """渲染状态标签 (Status Badge)"""
    colors = {
        "success": "var(--mt-ok)",
        "error": "var(--mt-danger)",
        "warning": "var(--mt-warn)",
        "info": "var(--mt-accent2)",
        "neutral": "var(--mt-text3)"
    }
    color = colors.get(status, colors["neutral"])
    st.markdown(
        f'<span style="display: inline-flex; align-items: center; gap: 6px; padding: 2px 8px; '
        f'border-radius: 4px; background: {color}; opacity: 0.8; color: var(--mt-bg0); border: 1px solid {color}; '
        f'font-size: 13px; font-weight: 600;">'
        f'{label}</span>',
        unsafe_allow_html=True
    )


def render_table_section(rows: list[dict], empty_message: str, hint: str | None = None) -> bool:
    """渲染统一表格区

    Returns:
        bool: 是否成功渲染了表格
    """
    if not rows:
        render_empty_state(empty_message, hint, icon="📋")
        return False

    st.dataframe(rows, use_container_width=True, hide_index=True)
    if hint:
        st.caption(hint)
    return True
