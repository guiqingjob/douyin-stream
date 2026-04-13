"""
资产大盘页面
"""

import sqlite3
import streamlit as st

from media_tools.web.constants import DOWNLOADS_DIR, TRANSCRIPTS_DIR
from media_tools.web.components.ui_patterns import (
    render_empty_state,
    render_page_header,
    render_summary_metrics,
    render_table_section,
    render_cta_section,
)
from media_tools.web.utils import format_size, format_timestamp, get_page_path
from media_tools.douyin.core.config_mgr import get_config

from media_tools.logger import get_logger
logger = get_logger('web')

def _get_db_path():
    return get_config().get_db_path()

def _fetch_assets(status_filter=None, limit=50):
    try:
        with sqlite3.connect(_get_db_path()) as conn:
            cursor = conn.cursor()
            query = "SELECT asset_id, creator_uid, title, duration, video_path, video_status, transcript_path, transcript_status, create_time, update_time FROM media_assets"
            params = []
            if status_filter:
                query += " WHERE video_status = ?"
                params.append(status_filter)
            query += " ORDER BY create_time DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"读取资产库失败: {e}")
        return []

render_page_header("📂 资产大盘", "全局查看已下载的素材与已生成的文稿。")

tab1, tab2 = st.tabs(["🎬 视频素材库", "📝 转写文稿库"])

with tab1:
    st.subheader("🎬 视频素材库")
    
    assets = _fetch_assets(status_filter='downloaded', limit=100)
    
    if not assets:
        render_empty_state("素材库为空。", "先去下载中心创建一个下载任务，拿到第一批素材。", icon="🎬")
    else:
        latest_name = assets[0][2][:40] if assets[0][2] else assets[0][0]
        latest_time = assets[0][8]
        
        render_summary_metrics(
            [
                {"label": "素材数量", "value": len(assets)},
                {"label": "最近入库", "value": latest_time.split("T")[0] if "T" in latest_time else latest_time},
                {"label": "最近文件", "value": latest_name},
            ]
        )

        render_table_section(
            [
                {
                    "博主 UID": a[1],
                    "标题": (a[2][:40] + "...") if a[2] and len(a[2]) > 40 else a[2],
                    "时长(秒)": a[3] // 1000 if a[3] else "-",
                    "相对路径": a[4],
                    "文稿状态": "✅" if a[7] == 'completed' else "⏳",
                    "入库时间": a[8].replace("T", " ")[:19] if a[8] else "-",
                }
                for a in assets
            ],
            empty_message="当前没有可展示的数据。",
            hint="如果素材已经确认无误，下一步通常是进入转写中心生成文稿。",
        )
        st.divider()
        if render_cta_section(
            "素材已准备就绪？",
            "将刚下载的视频批量生成为可编辑的文稿。",
            "🎙️ 去转写中心",
            "go_to_transcribe_from_library"
        ):
            st.switch_page(get_page_path("transcribe_center.py"))

with tab2:
    st.subheader("📝 转写文稿库")
    
    transcripts = [a for a in _fetch_assets(limit=100) if a[7] == 'completed']
    
    if not transcripts:
        render_empty_state("文稿库为空。", "先去转写中心创建一个任务。", icon="📝")
    else:
        latest_name = transcripts[0][2][:40] if transcripts[0][2] else transcripts[0][0]
        latest_time = transcripts[0][9]
        
        render_summary_metrics(
            [
                {"label": "文稿数量", "value": len(transcripts)},
                {"label": "最近生成", "value": latest_time.split("T")[0] if "T" in latest_time else latest_time},
                {"label": "最近文稿", "value": latest_name},
            ]
        )

        render_table_section(
            [
                {
                    "对应视频标题": (t[2][:40] + "...") if t[2] and len(t[2]) > 40 else t[2],
                    "文稿路径": t[6] if t[6] else "-",
                    "生成时间": t[9].replace("T", " ")[:19] if t[9] else "-",
                }
                for t in transcripts
            ],
            empty_message="当前没有可展示的数据。",
            hint="你可以直接在文件系统中打开这些 Markdown 文件进行编辑。",
        )
