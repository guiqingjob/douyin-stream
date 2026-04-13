#!/usr/bin/env python3
"""
Media Tools Web 管理面板 - Streamlit 版

启动方式:
    media-tools-web

生产部署:
    streamlit run src/media_tools/web/run.py --server.port 8501 --server.address 0.0.0.0
"""

import os
import sys
from pathlib import Path

try:
    from media_tools.douyin.core.config_mgr import get_config
    PROJECT_ROOT = get_config().project_root
except ImportError:
    PROJECT_ROOT = Path(os.getcwd())

from media_tools.db.core import init_db
from media_tools.logger import get_logger

logger = get_logger("web")


def init_project_dirs() -> None:
    """自动创建项目必需目录，并初始化数据库。"""
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

    try:
        from media_tools.web.constants import DB_FILE
        init_db(DB_FILE)
    except Exception as exc:
        print(f"❌ 数据库初始化失败: {exc}")


def main():
    import subprocess
    cmd = ["streamlit", "run", str(Path(__file__).resolve())]
    sys.exit(subprocess.call(cmd))


if __name__ == "__main__":
    init_project_dirs()

    import streamlit as st
    from media_tools.web.components.onboarding import render_onboarding
    from media_tools.web.navigation import build_navigation, get_navigation_summary
    from media_tools.web.theme import apply_global_theme

    st.set_page_config(
        page_title="Media Tools 工作台",
        page_icon="🎬",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    apply_global_theme()
    render_onboarding()

    from media_tools.web.constants import PROJECT_ROOT
    _FIRST_VISIT_FILE = PROJECT_ROOT / ".first_visit_done"

    if not _FIRST_VISIT_FILE.exists() or st.session_state.get("onboarding_step") is not None:
        st.sidebar.title("🎬 Media Tools")
        st.sidebar.caption("欢迎使用本地内容工作台")
        st.sidebar.info("请先完成右侧的新手引导流程")
        st.stop()

    with st.sidebar:
        st.title("🎬 Media Tools")
        st.caption("围绕“来源 → 素材 → 文稿”组织的本地内容工作台")
        st.divider()
        st.caption("页面分工")
        for title, summary in get_navigation_summary():
            st.markdown(f"- **{title}**：{summary}")
        st.divider()
        st.caption(f"项目路径: `{PROJECT_ROOT}`")

    build_navigation(st).run()
