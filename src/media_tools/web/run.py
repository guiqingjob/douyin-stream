#!/usr/bin/env python3
"""
Media Tools Web 管理面板 - Streamlit 版

启动方式:
    media-tools-web

生产部署:
    streamlit run src/media_tools/web/run.py --server.port 8501 --server.address 0.0.0.0
"""

import sys
from pathlib import Path
import os

# 动态获取项目根目录 (兼容安装包和源码运行)
try:
    from media_tools.douyin.core.config_mgr import get_config
    PROJECT_ROOT = get_config().project_root
except ImportError:
    PROJECT_ROOT = Path(os.getcwd())

from media_tools.logger import get_logger
from media_tools.db.core import init_db

logger = get_logger("web")

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
            
    # 初始化 V2 数据库
    try:
        from media_tools.web.constants import DB_FILE
        init_db(DB_FILE)
    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")

# 为 Streamlit 页面设置正确的相对路径
WEB_DIR = Path(__file__).resolve().parent

def main():
    import subprocess
    # 将此脚本作为 Streamlit app 运行
    cmd = ["streamlit", "run", str(Path(__file__).resolve())]
    sys.exit(subprocess.call(cmd))

if __name__ == "__main__":
    init_project_dirs()
    
    import streamlit as st
    from media_tools.web.components.onboarding import render_onboarding
    from media_tools.web.theme import apply_global_theme
    
    # ─────────────────────────────────────────────
    # 页面配置
    # ─────────────────────────────────────────────
    st.set_page_config(
        page_title="Media Tools 工作台",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    
    apply_global_theme()
    
    # 显示新手引导（仅首次访问）
    render_onboarding()
    
    # 如果正在进行新手引导，只显示引导相关的精简导航
    from media_tools.web.constants import PROJECT_ROOT
    from pathlib import Path
    _FIRST_VISIT_FILE = PROJECT_ROOT / ".first_visit_done"
    
    if not _FIRST_VISIT_FILE.exists() or st.session_state.get("onboarding_step") is not None:
        st.sidebar.title("🎬 Media Tools")
        st.sidebar.caption("欢迎使用本地内容工作台")
        st.sidebar.info("请先完成右侧的新手引导流程")
        st.stop()  # 停止渲染其余页面导航，强迫用户完成引导
    
    # ─────────────────────────────────────────────
    # 原生多页导航配置 (st.navigation)
    # ─────────────────────────────────────────────
    pg_home = st.Page(str(WEB_DIR / "pages/home.py"), title="仪表盘", icon="🏠", default=True)
    pg_download = st.Page(str(WEB_DIR / "pages/download_center.py"), title="下载中心", icon="📥")
    pg_transcribe = st.Page(str(WEB_DIR / "pages/transcribe_center.py"), title="转写中心", icon="🎙️")
    pg_assets = st.Page(str(WEB_DIR / "pages/asset_library.py"), title="资产大盘", icon="📂")
    
    pg_following = st.Page(str(WEB_DIR / "pages/following_mgmt.py"), title="关注管理", icon="👥")
    pg_accounts = st.Page(str(WEB_DIR / "pages/accounts.py"), title="账号与认证", icon="🔑")
    pg_cleanup = st.Page(str(WEB_DIR / "pages/cleanup.py"), title="存储清理", icon="🧹")
    pg_settings = st.Page(str(WEB_DIR / "pages/settings.py"), title="系统配置", icon="⚙️")
    
    with st.sidebar:
        st.title("🎬 Media Tools")
        st.caption("本地内容工作台")
        st.caption("下载素材 → 转写文稿 → 管理结果")
        st.divider()
    
    pg = st.navigation(
        {
            "核心工作流": [pg_home, pg_download, pg_transcribe],
            "资产管理": [pg_assets],
            "系统与配置": [pg_following, pg_accounts, pg_cleanup, pg_settings]
        }
    )
    
    with st.sidebar:
        st.divider()
        st.caption(f"项目路径: `{PROJECT_ROOT}`")
    
    # 启动页面
    pg.run()
