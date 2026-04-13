"""
资产大盘页面
"""

from __future__ import annotations

import sqlite3

import streamlit as st

from media_tools.douyin.core.config_mgr import get_config
from media_tools.logger import get_logger
from media_tools.web.components.ui_patterns import (
    render_cta_section,
    render_empty_state,
    render_page_header,
    render_summary_metrics,
)
from media_tools.web.services.status import get_system_status
from media_tools.web.utils import get_page_path

logger = get_logger('web')


def _get_db_path():
    return get_config().get_db_path()


def _fetch_assets(limit: int = 200) -> list[tuple]:
    try:
        with sqlite3.connect(_get_db_path()) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT asset_id, creator_uid, title, duration, video_path, video_status,
                       transcript_path, transcript_status, create_time, update_time
                FROM media_assets
                ORDER BY create_time DESC
                LIMIT ?
                """,
                (limit,),
            )
            return cursor.fetchall()
    except Exception as exc:
        logger.error(f'读取资产库失败: {exc}')
        return []


def _render_summary(rows: list[tuple]) -> dict:
    status = get_system_status()
    render_summary_metrics(
        [
            {'label': '本地素材', 'value': status['downloads_count']},
            {'label': '待转写', 'value': status['pending_transcripts']},
            {'label': '已完成文稿', 'value': status['transcripts_count']},
            {'label': '本地占用', 'value': status['storage_usage']},
        ]
    )
    return status


def _render_pending_assets(rows: list[tuple]) -> None:
    pending = [row for row in rows if row[5] == 'downloaded' and row[7] != 'completed']

    st.subheader('① 待处理资产')
    st.caption('这里优先展示还没完成转写的素材，因为这才是当前最值得处理的队列。')

    if not pending:
        render_empty_state('当前没有待处理资产。', '如果还没有素材，去下载中心获取；如果都已转写，可直接查看下方结果资产。', icon='✅')
        return

    preview_rows = []
    for asset in pending[:100]:
        preview_rows.append(
            {
                '博主 UID': asset[1],
                '标题': (asset[2][:40] + '...') if asset[2] and len(asset[2]) > 40 else asset[2],
                '时长(秒)': asset[3] // 1000 if asset[3] else '-',
                '视频路径': asset[4],
                '状态': '待转写',
                '入库时间': (asset[8] or '-').replace('T', ' ')[:19],
            }
        )
    st.dataframe(preview_rows, use_container_width=True, hide_index=True)


def _render_completed_assets(rows: list[tuple]) -> None:
    completed = [row for row in rows if row[7] == 'completed']

    st.subheader('② 已完成文稿')
    st.caption('这里展示已经走完整条链路的结果资产，重点看文稿产出。')

    if not completed:
        render_empty_state('当前还没有已完成文稿。', '先去转写中心跑通一批素材，再回来集中查看结果。', icon='📝')
        return

    preview_rows = []
    for asset in completed[:100]:
        preview_rows.append(
            {
                '对应视频标题': (asset[2][:40] + '...') if asset[2] and len(asset[2]) > 40 else asset[2],
                '博主 UID': asset[1],
                '文稿路径': asset[6] or '-',
                '更新时间': (asset[9] or '-').replace('T', ' ')[:19],
            }
        )
    st.dataframe(preview_rows, use_container_width=True, hide_index=True)


def _render_all_assets(rows: list[tuple]) -> None:
    st.subheader('③ 全部资产视图')
    st.caption('最后再给全量视图，避免用户一上来就淹没在所有历史数据里。')

    if not rows:
        render_empty_state('资产库为空。', '先去下载中心拿到第一批素材。', icon='📂')
        return

    table_rows = []
    for asset in rows[:150]:
        table_rows.append(
            {
                '博主 UID': asset[1],
                '标题': (asset[2][:36] + '...') if asset[2] and len(asset[2]) > 36 else asset[2],
                '视频状态': asset[5],
                '文稿状态': asset[7],
                '视频路径': asset[4] or '-',
                '文稿路径': asset[6] or '-',
                '创建时间': (asset[8] or '-').replace('T', ' ')[:19],
            }
        )
    st.dataframe(table_rows, use_container_width=True, hide_index=True)


render_page_header('📂 资产大盘', '优先看待处理资产，其次看已完成结果，最后再看全量明细。')
rows = _fetch_assets(limit=300)
status = _render_summary(rows)

_render_pending_assets(rows)
st.divider()
_render_completed_assets(rows)
st.divider()
_render_all_assets(rows)

if status['pending_transcripts'] > 0 and render_cta_section(
    '还有待处理素材？',
    '去转写中心继续把素材转成文稿。',
    '🎙️ 去转写中心',
    'go_transcribe_from_assets',
):
    st.switch_page(get_page_path('transcribe_center.py'))
elif status['downloads_count'] == 0 and render_cta_section(
    '资产库为空？',
    '去下载中心获取第一批素材。',
    '📥 去下载中心',
    'go_download_from_assets',
):
    st.switch_page(get_page_path('download_center.py'))
