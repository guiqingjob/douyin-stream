"""
工作台首页
"""

import streamlit as st

from web.components.home_cards import render_home_status_cards
from web.components.storage_chart import render_storage_chart
from web.components.task_table import render_task_table
from web.constants import (
    PAGE_DOWNLOAD,
    PAGE_FOLLOWING,
    PAGE_SETTINGS,
    PAGE_TRANSCRIBE,
)


# 渲染工作台首页
st.title("🏠 工作台")
st.caption("先确认系统状态，再开始下载素材或转写文稿。")

status = render_home_status_cards()

st.divider()
_render_next_step(status)

st.divider()
_render_quick_actions(status)

st.divider()
st.subheader("📌 最近任务")
st.caption("这里只显示最近 5 条历史，方便快速确认刚刚做了什么。")
render_task_table(limit=5)

st.divider()
render_storage_chart()


def _render_next_step(status: dict) -> None:
    """根据当前状态给出下一步建议"""
    missing_items = []

    if not status["env_ok"]:
        missing_items.append("环境检测")
    if not status["cookie_ok"]:
        missing_items.append("抖音 Cookie")
    if not status["qwen_ok"]:
        missing_items.append("Qwen 认证")

    if not missing_items:
        st.success("系统已就绪，可以直接开始下载素材或转写文稿。")

        col1, col2 = st.columns(2)
        with col1:
            st.info("推荐从 **下载中心** 开始，先获取一个样例视频。")
        with col2:
            st.info("如果你已经有本地文件，可以直接去 **转写中心**。")
        return

    st.warning(f"当前还缺少：{'、'.join(missing_items)}")
    st.info("建议先完成配置，再进入下载或转写流程，这样更容易一次跑通。")

    if st.button("⚙️ 去系统配置", type="primary", use_container_width=False, key="go_settings_from_home"):
        st.switch_page("web/pages/settings.py")


def _render_quick_actions(status: dict) -> None:
    """渲染快速操作区"""
    st.subheader("⚡ 常用入口")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        download_disabled = not status["cookie_ok"]
        if st.button(
            "📥 开始下载",
            use_container_width=True,
            type="primary",
            disabled=download_disabled,
            help="需要先配置抖音 Cookie" if download_disabled else None,
        ):
            st.switch_page("web/pages/download_center.py")

    with col2:
        transcribe_disabled = not status["qwen_ok"]
        if st.button(
            "🎙️ 开始转写",
            use_container_width=True,
            type="primary",
            disabled=transcribe_disabled,
            help="需要先完成 Qwen 认证" if transcribe_disabled else None,
        ):
            st.switch_page("web/pages/transcribe_center.py")

    with col3:
        if st.button("👥 管理来源", use_container_width=True):
            st.switch_page("web/pages/following_mgmt.py")

    with col4:
        if st.button("⚙️ 检查配置", use_container_width=True):
            st.switch_page("web/pages/settings.py")
