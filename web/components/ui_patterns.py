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


def render_empty_state(message: str, hint: str | None = None) -> None:
    """渲染统一空状态"""
    st.info(message)
    if hint:
        st.caption(hint)


def render_table_section(rows: list[dict], empty_message: str, hint: str | None = None) -> bool:
    """渲染统一表格区

    Returns:
        bool: 是否成功渲染了表格
    """
    if not rows:
        render_empty_state(empty_message, hint)
        return False

    st.dataframe(rows, use_container_width=True, hide_index=True)
    if hint:
        st.caption(hint)
    return True
