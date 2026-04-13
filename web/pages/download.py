"""
DEPRECATED: 旧版下载页面

已被以下页面替代：
- `web/pages/download.py` -> `web/pages/download_center.py`

说明：
- 当前主路由 `web_app.py` 已不再引用本文件
- 保留此文件仅用于过渡和兼容排查
- 如有旧入口仍引用本文件，将自动转到新版下载中心
"""

import streamlit as st

from web.pages.download_center import render_download_center


def render_download() -> None:
    """渲染旧版下载页面（已废弃）"""
    st.warning("此页面已废弃，已自动切换到新版“📥 下载中心”。")
    render_download_center()
