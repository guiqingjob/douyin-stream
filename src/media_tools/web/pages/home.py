"""
工作台首页
"""

import streamlit as st

from media_tools.logger import get_logger
from media_tools.web.components.home_cards import render_home_status_cards
from media_tools.web.components.storage_chart import render_storage_chart
from media_tools.web.components.task_table import render_task_table
from media_tools.web.components.ui_patterns import render_cta_section, render_page_header
from media_tools.web.utils import get_page_path

logger = get_logger('web')


def _render_next_step(status: dict) -> None:
    target = status.get("next_page", "settings.py")
    workflow_stage = status.get("workflow_stage", "先完成基础配置")

    with st.container(border=True):
        col_a, col_b = st.columns([3, 2], gap="large", vertical_alignment="center")
        with col_a:
            st.markdown(f"#### 🎯 当前建议：{workflow_stage}")
            st.caption(
                "这个工作台现在按“来源 → 素材 → 文稿 → 维护”组织。"
                "不要同时在多个页面来回跳，先跑通一个清晰的链路。"
            )

            bullets = []
            if not status["env_ok"]:
                bullets.append("先去系统配置完成环境检测")
            if not status["cookie_ok"]:
                bullets.append("补齐抖音 Cookie，打通下载入口")
            if status["source_count"] == 0:
                bullets.append("先添加至少一个来源，批量拉取才有意义")
            if status["downloads_count"] > 0 and not status["qwen_ok"]:
                bullets.append("下载链路已具备，下一步补齐转写认证")
            if status["pending_transcripts"] > 0:
                bullets.append(f"当前还有 {status['pending_transcripts']} 条素材待转写")

            for item in bullets[:4]:
                st.markdown(f"- {item}")

        with col_b:
            if render_cta_section(
                "进入当前最合适的页面",
                f"根据现状，建议先去：`{target}`",
                "➡️ 继续处理",
                "home_next_step",
            ):
                st.switch_page(get_page_path(target))


def _render_quick_actions(status: dict) -> None:
    st.subheader("⚡ 核心操作")

    col1, col2, col3 = st.columns(3, gap="medium")
    with col1:
        if st.button(
            "📥 获取素材",
            use_container_width=True,
            type="primary",
            disabled=not status["cookie_ok"],
            help=None if status["cookie_ok"] else "请先完成抖音认证",
        ):
            st.switch_page(get_page_path("download_center.py"))
    with col2:
        if st.button(
            "🎙️ 处理转写",
            use_container_width=True,
            type="secondary",
            disabled=not status["qwen_ok"],
            help=None if status["qwen_ok"] else "请先完成 Qwen 认证",
        ):
            st.switch_page(get_page_path("transcribe_center.py"))
    with col3:
        if st.button("📂 查看资产", use_container_width=True, type="secondary"):
            st.switch_page(get_page_path("asset_library.py"))

    col4, col5, col6 = st.columns(3, gap="medium")
    with col4:
        if st.button("👥 管理来源", use_container_width=True):
            st.switch_page(get_page_path("following_mgmt.py"))
    with col5:
        if st.button("🔑 账号认证", use_container_width=True):
            st.switch_page(get_page_path("accounts.py"))
    with col6:
        if st.button("⚙️ 系统维护", use_container_width=True):
            st.switch_page(get_page_path("settings.py"))


render_page_header("🏠 工作台", "先看系统状态与当前阶段，再进入一个明确页面完成单一任务。")

status = render_home_status_cards()
_render_next_step(status)

st.divider()
_render_quick_actions(status)

st.divider()
st.subheader("📌 最近任务")
st.caption("按工作流拆开看，不把下载和转写混在一起。")

tab1, tab2 = st.tabs(["📥 下载任务", "🎙️ 转写任务"])
with tab1:
    render_task_table(limit=5, task_types=["download", "batch_download"])
with tab2:
    render_task_table(limit=5, task_types=["transcribe", "batch_transcribe"])

st.divider()
render_storage_chart()
