"""
DEPRECATED: 旧版关注管理页面

已被以下页面替代：
- `web/pages/following.py` -> `web/pages/following_mgmt.py`

说明：
- 当前主路由 `web_app.py` 已不再引用本文件
- 保留此文件仅用于过渡和兼容排查
- 如有旧入口仍引用本文件，将自动转到新版关注管理
"""

import streamlit as st

from web.pages.following_mgmt import render_following_mgmt


def render_following() -> None:
    """渲染旧版关注页面（已废弃）"""
    st.warning("此页面已废弃，已自动切换到新版“👥 关注管理”。")
    render_following_mgmt()
