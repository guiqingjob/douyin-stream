"""
工作台状态卡片组件
"""

from pathlib import Path

import streamlit as st

from media_tools.web.constants import DOWNLOADS_DIR, QWEN_AUTH_PATH, TRANSCRIPTS_DIR
from media_tools.web.utils import format_size

from media_tools.logger import get_logger
logger = get_logger('web')



def render_home_status_cards() -> dict:
    """渲染工作台状态卡片

    Returns:
        dict: 系统状态信息
    """
    status = {
        "cookie_ok": False,
        "qwen_ok": False,
        "env_ok": False,
        "storage_usage": "0 B",
        "storage_total": 0,
        "downloads_count": 0,
        "transcripts_count": 0,
    }

    # 检查 Cookie 状态
    try:
        from media_tools.douyin.core.config_mgr import get_config

        status["cookie_ok"] = get_config().has_cookie()
    except Exception:
        logger.exception('发生异常')
        pass

    # 检查 Qwen 认证
    try:
        from media_tools.douyin.core.config_mgr import get_config
        import sqlite3
        
        cfg = get_config()
        with sqlite3.connect(cfg.get_db_path()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM auth_credentials WHERE platform = 'qwen' AND is_valid = 1")
            status["qwen_ok"] = cursor.fetchone() is not None
    except Exception:
        # Fallback 到旧版文件检查
        status["qwen_ok"] = QWEN_AUTH_PATH.exists() and QWEN_AUTH_PATH.stat().st_size > 50

    # 检查环境
    try:
        from media_tools.douyin.core.env_check import check_all

        passed, _ = check_all()
        status["env_ok"] = passed
    except Exception:
        logger.exception('发生异常')
        pass

    # 统计素材与文稿
    if DOWNLOADS_DIR.exists():
        try:
            status["downloads_count"] = sum(1 for f in DOWNLOADS_DIR.rglob("*.mp4") if f.is_file())
        except Exception:
            logger.exception('发生异常')
            pass

    if TRANSCRIPTS_DIR.exists():
        try:
            status["transcripts_count"] = sum(1 for f in TRANSCRIPTS_DIR.rglob("*.md") if f.is_file())
        except Exception:
            logger.exception('发生异常')
            pass

    # 计算存储使用
    total_size = 0
    for directory in [DOWNLOADS_DIR, TRANSCRIPTS_DIR]:
        if directory.exists():
            try:
                total_size += sum(f.stat().st_size for f in directory.rglob("*") if f.is_file())
            except Exception:
                logger.exception('发生异常')
                pass

    status["storage_usage"] = format_size(total_size)
    status["storage_total"] = total_size

    # 显示状态卡片
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "抖音下载认证",
            "已就绪" if status["cookie_ok"] else "待配置",
            delta="Cookie 可用" if status["cookie_ok"] else "需要 Cookie",
            border=True,
        )

    with col2:
        st.metric(
            "转写认证状态",
            "已就绪" if status["qwen_ok"] else "待配置",
            delta="Qwen 可用" if status["qwen_ok"] else "需要认证",
            border=True,
        )

    with col3:
        st.metric(
            "本地素材数",
            str(status["downloads_count"]),
            delta=f"文稿 {status['transcripts_count']} 篇",
            border=True,
        )

    with col4:
        st.metric(
            "本地占用",
            status["storage_usage"],
            delta="环境通过" if status["env_ok"] else "请先做环境检测",
            border=True,
        )

    return status
