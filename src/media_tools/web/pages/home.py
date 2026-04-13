"""
工作台首页
"""

import streamlit as st

from media_tools.web.components.home_cards import render_home_status_cards
from media_tools.web.components.storage_chart import render_storage_chart
from media_tools.web.components.task_table import render_task_table
from media_tools.logger import get_logger
logger = get_logger('web')
from media_tools.web.components.ui_patterns import render_page_header
from media_tools.web.utils import get_page_path


# 渲染工作台首页
def _render_next_step(status: dict) -> None:
    """根据当前状态给出下一步建议"""
    missing_items = []

    if not status["env_ok"]:
        missing_items.append("环境检测")
    if not status["cookie_ok"]:
        missing_items.append("抖音 Cookie")
    if not status["qwen_ok"]:
        missing_items.append("Qwen 认证")

    with st.container(border=True):
        col_a, col_b = st.columns([3, 2], gap="large", vertical_alignment="center")
        with col_a:
            if not missing_items:
                st.markdown("#### ✅ 系统已就绪")
                st.caption("建议先从下载中心获取一条样例素材，跑通“下载 → 转写 → 管理”的完整链路。")
            else:
                st.markdown("#### ⚙️ 建议先完成配置")
                st.caption(f"当前仍缺少：{'、'.join(missing_items)}。先配置好环境与认证，再开始下载/转写会更顺畅。")

        with col_b:
            if not missing_items:
                col1, col2 = st.columns(2, gap="small")
                with col1:
                    if st.button("📥 开始下载", type="primary", use_container_width=True, key="cta_download_from_home"):
                        st.switch_page(get_page_path("download_center.py"))
                with col2:
                    if st.button("🎙️ 去转写", type="secondary", use_container_width=True, key="cta_transcribe_from_home"):
                        st.switch_page(get_page_path("transcribe_center.py"))
            else:
                if st.button("⚙️ 去系统配置", type="primary", use_container_width=True, key="cta_settings_from_home"):
                    st.switch_page(get_page_path("settings.py"))
                if st.button("🔑 账号与认证", type="secondary", use_container_width=True, key="cta_accounts_from_home"):
                    st.switch_page(get_page_path("accounts.py"))


def _render_quick_actions(status: dict) -> None:
    """渲染快速操作区"""
    st.subheader("⚡ 常用入口")

    col1, col2 = st.columns(2, gap="medium")
    with col1:
        download_disabled = not status["cookie_ok"]
        if st.button(
            "📥 开始下载",
            use_container_width=True,
            type="primary",
            disabled=download_disabled,
            help="需要先配置抖音 Cookie" if download_disabled else None,
            key="quick_download",
        ):
            st.switch_page(get_page_path("download_center.py"))

    with col2:
        transcribe_disabled = not status["qwen_ok"]
        if st.button(
            "🎙️ 开始转写",
            use_container_width=True,
            type="secondary",
            disabled=transcribe_disabled,
            help="需要先完成 Qwen 认证" if transcribe_disabled else None,
            key="quick_transcribe",
        ):
            st.switch_page(get_page_path("transcribe_center.py"))

    col3, col4 = st.columns(2, gap="medium")
    with col3:
        if st.button("👥 管理来源", use_container_width=True, type="secondary", key="quick_following"):
            st.switch_page(get_page_path("following_mgmt.py"))

    with col4:
        if st.button("⚙️ 系统配置", use_container_width=True, type="secondary", key="quick_settings"):
            st.switch_page(get_page_path("settings.py"))
render_page_header("🏠 工作台", "先确认系统状态，再开始下载素材或转写文稿。")

status = render_home_status_cards()

_render_next_step(status)

st.divider()
_render_quick_actions(status)

st.divider()
st.subheader("📌 最近任务")
st.caption("这里只显示最近 5 条历史，方便快速确认刚刚做了什么。")
render_task_table(limit=5)

st.divider()
render_storage_chart()
