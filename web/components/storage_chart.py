"""
存储使用图表组件
"""

import streamlit as st
from pathlib import Path

from web.constants import DOWNLOADS_DIR, PROJECT_ROOT, TRANSCRIPTS_DIR
from web.utils import format_size

from media_tools.logger import get_logger
logger = get_logger('web')



def render_storage_chart() -> None:
    """渲染存储使用图表"""
    st.subheader("💾 存储使用")
    
    # 计算各目录大小
    sizes = {
        "下载目录": _get_dir_size(DOWNLOADS_DIR),
        "转写目录": _get_dir_size(TRANSCRIPTS_DIR),
        "其他": _get_other_size(),
    }
    
    total = sum(sizes.values())
    
    # 显示进度条
    if total > 0:
        # 简化的进度显示（假设 10GB 上限）
        max_size = 10 * 1024 * 1024 * 1024  # 10 GB
        usage_percent = min(total / max_size * 100, 100)
        
        st.progress(usage_percent / 100)
        st.caption(f"{format_size(total)} / 10 GB ({usage_percent:.1f}%)")
        
        # 显示各部分占比
        cols = st.columns(len(sizes))
        for (name, size), col in zip(sizes.items(), cols):
            if size > 0:
                percent = size / total * 100
                col.metric(name, format_size(size), f"{percent:.0f}%")
    else:
        st.info("暂无数据占用存储")


def _get_dir_size(directory: Path) -> int:
    """计算目录大小"""
    if not directory.exists():
        return 0
    try:
        return sum(f.stat().st_size for f in directory.rglob("*") if f.is_file())
    except Exception:
        logger.exception('发生异常')
        return 0


def _get_other_size() -> int:
    """计算其他文件占用（数据库、配置、认证等）"""
    other_dirs = [
        PROJECT_ROOT / ".auth",
        PROJECT_ROOT / "config",
        PROJECT_ROOT / "backups",
    ]
    
    total = 0
    for d in other_dirs:
        if d.exists():
            try:
                total += sum(f.stat().st_size for f in d.rglob("*") if f.is_file())
            except Exception:
                logger.exception('发生异常')
                pass
    
    # 加上数据库文件
    db_file = PROJECT_ROOT / "media_tools.db"
    if db_file.exists():
        total += db_file.stat().st_size
    
    return total
