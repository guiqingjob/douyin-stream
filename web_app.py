#!/usr/bin/env python3
"""
Media Tools Web 管理面板 - Streamlit 版

启动方式:
    streamlit run web_app.py

生产部署:
    streamlit run web_app.py --server.port 8501 --server.address 0.0.0.0
"""

import sys
from pathlib import Path

# 确保项目根目录在 Python 路径中
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 确保 scripts/ 也在路径中（旧版模块）
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if SCRIPTS_DIR.exists() and str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import streamlit as st

from web.pages.dashboard import render_dashboard
from web.pages.following import render_following
from web.pages.download import render_download
from web.pages.transcribe import render_transcribe
from web.pages.accounts import render_accounts
from web.pages.cleanup import render_cleanup
from web.pages.settings import render_settings


# ─────────────────────────────────────────────
# 页面配置
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Media Tools 管理面板",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# 侧边栏导航
# ─────────────────────────────────────────────
with st.sidebar:
    st.title("🎬 Media Tools")
    st.caption("抖音下载 + AI 转写 Web 管理面板")
    st.divider()

    page = st.radio(
        "导航菜单",
        [
            "📊 仪表盘",
            "👤 关注管理",
            "📥 下载任务",
            "🎙️ 转写任务",
            "🔑 账号管理",
            "🗑️ 数据清理",
            "⚙️ 系统设置",
        ],
        index=0,
        label_visibility="collapsed",
    )

    st.divider()
    st.caption(f"项目路径: `{PROJECT_ROOT}`")

# ─────────────────────────────────────────────
# 页面路由
# ─────────────────────────────────────────────
if page == "📊 仪表盘":
    render_dashboard()
elif page == "👤 关注管理":
    render_following()
elif page == "📥 下载任务":
    render_download()
elif page == "🎙️ 转写任务":
    render_transcribe()
elif page == "🔑 账号管理":
    render_accounts()
elif page == "🗑️ 数据清理":
    render_cleanup()
elif page == "⚙️ 系统设置":
    render_settings()
