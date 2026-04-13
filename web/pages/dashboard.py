"""
DEPRECATED: 旧版仪表盘页面

已被以下页面替代：
- `web/pages/dashboard.py` -> `web/pages/home.py`

说明：
- 当前主路由 `web_app.py` 已不再引用本文件
- 保留此文件仅用于过渡和兼容排查
- 如有旧入口仍引用本文件，将自动转到新版工作台
"""

import streamlit as st

from web.pages.home import render_home


def render_dashboard() -> None:
    """渲染旧版仪表盘页面（已废弃）"""
    st.warning("此页面已废弃，已自动切换到新版“🏠 工作台”。")
    render_home()
