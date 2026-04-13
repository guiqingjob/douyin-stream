"""
认证状态卡片组件
"""

from __future__ import annotations

import streamlit as st

from media_tools.logger import get_logger
from media_tools.web.components.ui_patterns import render_summary_metrics
from media_tools.web.services.status import check_douyin_auth, check_qwen_auth

logger = get_logger('web')


def render_auth_status_card() -> None:
    """渲染轻量认证状态摘要卡。"""
    try:
        douyin_auth = check_douyin_auth()
    except Exception:
        logger.exception('检查抖音认证状态失败')
        douyin_auth = False

    try:
        qwen_auth = check_qwen_auth()
    except Exception:
        logger.exception('检查 Qwen 认证状态失败')
        qwen_auth = False

    render_summary_metrics(
        [
            {'label': '抖音认证', 'value': '已就绪' if douyin_auth else '未认证'},
            {'label': 'Qwen 认证', 'value': '已就绪' if qwen_auth else '未认证'},
        ]
    )

    if not douyin_auth or not qwen_auth:
        st.caption('缺少认证时，可前往「账号与认证」页面补齐下载或转写所需授权。')
