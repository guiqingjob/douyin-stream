"""
DEPRECATED: 旧版转写页面

已被以下页面替代：
- `web/pages/transcribe.py` -> `web/pages/transcribe_center.py`

说明：
- 当前主路由 `web_app.py` 已不再引用本文件
- 保留此文件仅用于过渡和兼容排查
- 如有旧入口仍引用本文件，将自动转到新版转写中心
"""

import streamlit as st

from web.pages.transcribe_center import render_transcribe_center


def render_transcribe() -> None:
    """渲染旧版转写页面（已废弃）"""
    st.warning("此页面已废弃，已自动切换到新版“🎙️ 转写中心”。")
    render_transcribe_center()
