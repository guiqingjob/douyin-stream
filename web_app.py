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
# 原生多页导航配置 (st.navigation)
# ─────────────────────────────────────────────
pg_home = st.Page("web/pages/home.py", title="仪表盘", icon="🏠", default=True)
pg_download = st.Page("web/pages/download_center.py", title="下载中心", icon="📥")
pg_transcribe = st.Page("web/pages/transcribe_center.py", title="转写中心", icon="🎙️")

pg_following = st.Page("web/pages/following_mgmt.py", title="关注管理", icon="👥")
pg_accounts = st.Page("web/pages/accounts.py", title="账号与认证", icon="🔑")
pg_cleanup = st.Page("web/pages/cleanup.py", title="存储清理", icon="🧹")
pg_settings = st.Page("web/pages/settings.py", title="系统配置", icon="⚙️")

pg = st.navigation(
    {
        "核心工作流": [pg_home, pg_download, pg_transcribe],
        "系统与配置": [pg_following, pg_accounts, pg_cleanup, pg_settings]
    }
)

with st.sidebar:
    st.title("🎬 Media Tools")
    st.caption("本地内容工作台")
    st.caption("下载素材 → 转写文稿 → 管理结果")
    st.divider()
    st.caption(f"项目路径: `{PROJECT_ROOT}`")

# 启动页面
pg.run()
