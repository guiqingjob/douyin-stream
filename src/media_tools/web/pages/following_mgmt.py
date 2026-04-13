"""
关注管理页面
"""

from __future__ import annotations

import json

import streamlit as st

from media_tools.logger import get_logger
from media_tools.web.components.ui_patterns import (
    render_cta_section,
    render_danger_zone,
    render_empty_state,
    render_page_header,
    render_summary_metrics,
)
from media_tools.web.services.status import get_system_status
from media_tools.web.utils import get_page_path

logger = get_logger('web')


def _load_users() -> list[dict]:
    try:
        from media_tools.douyin.core.following_mgr import list_users
        return list_users()
    except Exception as exc:
        logger.exception('加载来源列表失败')
        st.error(f'加载来源列表失败: {exc}')
        return []


def _render_source_summary(users: list[dict]) -> None:
    named_users = sum(1 for user in users if user.get('nickname', user.get('name', '')).strip())
    active_users = sum(1 for user in users if user.get('sync_status') == 'active')
    render_summary_metrics(
        [
            {'label': '来源数量', 'value': len(users)},
            {'label': '活跃来源', 'value': active_users},
            {'label': '已命名来源', 'value': named_users},
            {'label': '待补全昵称', 'value': len(users) - named_users},
        ]
    )


def _render_add_source() -> None:
    with st.container(border=True):
        st.subheader('① 添加来源')
        st.caption('来源管理首先回答一个问题：你准备持续跟踪哪些博主。')

        url = st.text_input(
            '抖音主页链接',
            placeholder='https://www.douyin.com/user/MS4wLjABAAAA...',
        )

        if st.button('➕ 添加来源', type='primary', use_container_width=True):
            if not url:
                st.warning('请输入链接')
                return

            with st.spinner('正在获取用户信息...'):
                ok, user = _add_user(url)
                if ok and user:
                    st.success(f"✅ 添加成功: {user.get('nickname', user.get('uid', '未知'))}")
                    st.rerun()
                else:
                    st.error('添加失败，请检查链接是否正确或 Cookie 是否有效')


def _render_source_list(users: list[dict]) -> None:
    with st.container(border=True):
        st.subheader('② 当前来源列表')
        st.caption('这里只处理“来源维护”，不把导入导出和删除危险操作放在主视线中央。')

        if not users:
            render_empty_state('来源列表为空。', '先添加一个博主主页链接，后续才能按来源批量拉取素材。', icon='👥')
            return

        sort_col, search_col = st.columns([1, 1])
        with sort_col:
            sort_by = st.selectbox('排序方式', ['默认', 'UID', '昵称'])
        with search_col:
            search = st.text_input('搜索来源', placeholder='输入昵称或 UID')

        filtered_users = users[:]
        if sort_by == 'UID':
            filtered_users = sorted(filtered_users, key=lambda user: user.get('uid', ''))
        elif sort_by == '昵称':
            filtered_users = sorted(filtered_users, key=lambda user: user.get('nickname', user.get('name', '')))

        if search:
            filtered_users = [
                user for user in filtered_users
                if search.lower() in user.get('nickname', user.get('name', '')).lower() or search in user.get('uid', '')
            ]

        if not filtered_users:
            render_empty_state('没有符合搜索条件的来源。', '清空搜索条件后重试。', icon='🔍')
            return

        rows = []
        for user in filtered_users:
            rows.append(
                {
                    'UID': user.get('uid', ''),
                    '昵称': user.get('nickname', user.get('name', '未知')),
                    '状态': '正常' if user.get('sync_status') == 'active' else '暂停',
                    '最后拉取': user.get('last_fetch_time', '-')[:19].replace('T', ' '),
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)
        st.caption('如果来源已经整理好，下一步通常是去下载中心按来源批量拉取素材。')


def _render_import_export(users: list[dict]) -> None:
    with st.container(border=True):
        st.subheader('③ 导入 / 导出')
        st.caption('这是辅助操作，用于迁移和备份，不应该干扰日常来源维护。')

        col1, col2 = st.columns(2)
        with col1:
            st.markdown('**导出来源**')
            data = _export_users(users)
            if data:
                st.download_button(
                    label='📥 下载 JSON',
                    data=data,
                    file_name='following.json',
                    mime='application/json',
                    use_container_width=True,
                )
            else:
                render_empty_state('暂无可导出的来源数据。', icon='📦')

        with col2:
            st.markdown('**导入来源**')
            uploaded = st.file_uploader('上传 JSON 文件', type=['json'])
            if uploaded and st.button('📤 开始导入', use_container_width=True):
                content = uploaded.read().decode('utf-8')
                ok, msg = _import_users(content)
                if ok:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)


def _render_danger_zone() -> None:
    with st.container(border=True):
        st.subheader('④ 危险操作')
        st.caption('删除来源是低频操作，单独收口，避免误操作。')

        del_uid = st.text_input('输入要删除的 UID')
        delete_local = st.checkbox('同时删除本地下载的视频文件')
        if del_uid and render_danger_zone(
            f'确认删除 UID {del_uid} 的来源?',
            '此操作不可逆；如果勾选同步删除本地文件，相关视频也会被删除。',
            '删除来源',
            f'del_{del_uid}',
        ):
            try:
                from media_tools.douyin.core.following_mgr import remove_user
                success = remove_user(del_uid, delete_local=delete_local)
                if success:
                    st.success(f'已成功删除来源: {del_uid}')
                    st.rerun()
                else:
                    st.error(f'删除失败，请检查 UID 是否正确: {del_uid}')
            except Exception as exc:
                logger.exception('删除来源失败')
                st.error(f'删除失败: {exc}')


def _add_user(url: str) -> tuple:
    try:
        from media_tools.douyin.core.following_mgr import add_user
        return add_user(url)
    except Exception as exc:
        logger.exception('添加来源失败')
        return False, str(exc)


def _export_users(users: list[dict]) -> str:
    try:
        return json.dumps({'users': users}, ensure_ascii=False, indent=2)
    except Exception:
        logger.exception('导出来源失败')
        return ''


def _import_users(content: str) -> tuple:
    try:
        data = json.loads(content)
        users = data.get('users', data if isinstance(data, list) else [])

        from datetime import datetime
        import sqlite3
        from media_tools.douyin.core.config_mgr import get_config

        count = 0
        db_path = get_config().get_db_path()
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            for user in users:
                uid = user.get('uid')
                sec_user_id = user.get('sec_user_id', '')
                nickname = user.get('nickname', user.get('name', ''))
                if uid:
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO creators
                        (uid, sec_user_id, nickname, platform, sync_status, last_fetch_time)
                        VALUES (?, ?, ?, 'douyin', 'active', ?)
                        """,
                        (uid, sec_user_id, nickname, datetime.now().isoformat()),
                    )
                    count += 1
            conn.commit()
        return True, f'成功导入 {count} 个来源'
    except Exception as exc:
        logger.exception('导入来源失败')
        return False, f'导入失败: {exc}'


render_page_header('👥 关注管理', '先明确要跟踪哪些来源，再去下载中心做批量拉取。')
status = get_system_status()
users = _load_users()
_render_source_summary(users)

col1, col2 = st.columns([1, 1], gap='large')
with col1:
    _render_add_source()
with col2:
    _render_source_list(users)

st.divider()
_render_import_export(users)
st.divider()
_render_danger_zone()

if len(users) > 0 and render_cta_section(
    '来源已准备好？',
    '去下载中心按来源批量拉取素材。',
    '📥 去下载中心',
    'go_download_from_following',
):
    st.switch_page(get_page_path('download_center.py'))
elif len(users) == 0 and status['cookie_ok'] and render_cta_section(
    '还没开始？',
    '先添加至少一个来源，工作台才能形成稳定的下载流程。',
    '🏠 回到工作台',
    'back_home_from_following',
):
    st.switch_page(get_page_path('home.py'))
