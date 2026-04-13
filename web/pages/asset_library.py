"""
资产大盘页面
"""

import streamlit as st

from web.constants import DOWNLOADS_DIR, TRANSCRIPTS_DIR
from web.components.ui_patterns import render_empty_state, render_summary_metrics, render_table_section, render_highlight_card
from web.utils import format_size, format_timestamp

st.title("📂 资产大盘")
st.caption("全局查看已下载的素材与已生成的文稿。")

tab1, tab2 = st.tabs(["🎬 视频素材库", "📝 转写文稿库"])

with tab1:
    st.subheader("🎬 视频素材库")
    if not DOWNLOADS_DIR.exists():
        render_empty_state("素材目录不存在。", "如果这是首次使用，先去下载中心创建一个下载任务。")
    else:
        video_files = list(DOWNLOADS_DIR.rglob("*.mp4"))
        total_size = sum(f.stat().st_size for f in video_files)
        sorted_files = sorted(video_files, key=lambda x: x.stat().st_mtime, reverse=True)

        latest_name = "-"
        latest_time = "-"
        if sorted_files:
            latest_name = sorted_files[0].name[:40]
            latest_time = format_timestamp(sorted_files[0].stat().st_mtime)

        render_summary_metrics(
            [
                {"label": "素材数量", "value": len(video_files)},
                {"label": "总占用", "value": format_size(total_size)},
                {"label": "最近入库", "value": latest_time},
                {"label": "最近文件", "value": latest_name},
            ]
        )

        if not sorted_files:
            render_empty_state("素材库为空。", "先去下载中心创建一个下载任务，拿到第一批素材。")
        else:
            render_table_section(
                [
                    {
                        "文件名": f.name[:60],
                        "大小": format_size(f.stat().st_size),
                        "修改时间": format_timestamp(f.stat().st_mtime),
                    }
                    for f in sorted_files[:30]
                ],
                empty_message="当前没有可展示的数据。",
                hint="如果素材已经确认无误，下一步通常是进入转写中心生成文稿。",
            )
            if st.button("🎙️ 用这些素材去转写", key="go_to_transcribe_from_library"):
                st.switch_page("web/pages/transcribe_center.py")

with tab2:
    st.subheader("📝 转写文稿库")
    if not TRANSCRIPTS_DIR.exists():
        render_empty_state("文稿目录不存在。", "如果这是首次使用，先去转写中心创建一个转写任务。")
    else:
        md_files = list(TRANSCRIPTS_DIR.rglob("*.md"))
        total_size = sum(f.stat().st_size for f in md_files)
        sorted_files = sorted(md_files, key=lambda x: x.stat().st_mtime, reverse=True)

        latest_name = "-"
        latest_time = "-"
        if sorted_files:
            latest_name = sorted_files[0].name[:40]
            latest_time = format_timestamp(sorted_files[0].stat().st_mtime)

        render_summary_metrics(
            [
                {"label": "文稿数量", "value": len(md_files)},
                {"label": "总占用", "value": format_size(total_size)},
                {"label": "最近生成", "value": latest_time},
                {"label": "最近文稿", "value": latest_name},
            ]
        )

        if not sorted_files:
            render_empty_state("文稿库为空。", "先去转写中心创建一个任务。")
        else:
            render_table_section(
                [
                    {
                        "文件名": f.name[:60],
                        "大小": format_size(f.stat().st_size),
                        "生成时间": format_timestamp(f.stat().st_mtime),
                    }
                    for f in sorted_files[:30]
                ],
                empty_message="当前没有可展示的数据。",
                hint="你可以直接在文件系统中打开这些 Markdown 文件进行编辑。",
            )
