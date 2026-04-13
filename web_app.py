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


# ─────────────────────────────────────────────
# 项目初始化：自动创建必需目录
# ─────────────────────────────────────────────
def init_project_dirs():
    """自动创建项目必需的目录"""
    required_dirs = [
        PROJECT_ROOT / "downloads",
        PROJECT_ROOT / "transcripts",
        PROJECT_ROOT / "temp_uploads",
        PROJECT_ROOT / ".auth",
        PROJECT_ROOT / "config",
        PROJECT_ROOT / "config" / "transcribe",
    ]

    for dir_path in required_dirs:
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ 创建目录: {dir_path}")


init_project_dirs()

import streamlit as st

from web.components.onboarding import render_onboarding
from web.constants import (
    NAV_PAGES,
    PAGE_ACCOUNTS,
    PAGE_CLEANUP,
    PAGE_DOWNLOAD,
    PAGE_FOLLOWING,
    PAGE_HOME,
    PAGE_SETTINGS,
    PAGE_TRANSCRIBE,
)
from web.pages.accounts import render_accounts
from web.pages.cleanup import render_cleanup
from web.pages.download_center import render_download_center
from web.pages.following_mgmt import render_following_mgmt
from web.pages.home import render_home
from web.pages.settings import render_settings
from web.pages.transcribe_center import render_transcribe_center


# ─────────────────────────────────────────────
# 页面配置
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Media Tools 工作台",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 显示新手引导（仅首次访问）
render_onboarding()

# ─────────────────────────────────────────────
# 侧边栏导航
# ─────────────────────────────────────────────
if "current_page" not in st.session_state:
    st.session_state.current_page = PAGE_HOME

with st.sidebar:
    st.title("🎬 Media Tools")
    st.caption("本地内容工作台")
    st.caption("下载素材 → 转写文稿 → 管理结果")
    st.divider()

    page_idx = NAV_PAGES.index(st.session_state.current_page) if st.session_state.current_page in NAV_PAGES else 0
    page = st.radio(
        "导航菜单",
        NAV_PAGES,
        index=page_idx,
        label_visibility="collapsed",
        key="page_radio",
    )
    st.session_state.current_page = page

    st.divider()
    st.markdown("**推荐路径**")
    st.caption("1. 系统配置\n2. 下载中心\n3. 转写中心")
    st.divider()
    st.caption(f"项目路径: `{PROJECT_ROOT}`")

# ─────────────────────────────────────────────
# 页面路由
# ─────────────────────────────────────────────
if st.session_state.current_page == PAGE_HOME:
    render_home()
elif st.session_state.current_page == PAGE_DOWNLOAD:
    render_download_center()
elif st.session_state.current_page == PAGE_TRANSCRIBE:
    render_transcribe_center()
elif st.session_state.current_page == PAGE_FOLLOWING:
    render_following_mgmt()
elif st.session_state.current_page == PAGE_ACCOUNTS:
    render_accounts()
elif st.session_state.current_page == PAGE_CLEANUP:
    render_cleanup()
elif st.session_state.current_page == PAGE_SETTINGS:
    render_settings()
