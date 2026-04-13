"""
清理与备份页面
"""

from __future__ import annotations

import time
from pathlib import Path

import streamlit as st

from media_tools.logger import get_logger
from media_tools.web.components.ui_patterns import (
    render_cta_section,
    render_danger_zone,
    render_empty_state,
    render_page_header,
    render_summary_metrics,
)
from media_tools.web.constants import DB_FILE, DOWNLOADS_DIR, LOGS_DIR, PROJECT_ROOT
from media_tools.web.services.status import get_system_status
from media_tools.web.utils import format_size, get_page_path

logger = get_logger('web')


def _collect_space_summary() -> dict:
    video_files = list(DOWNLOADS_DIR.rglob('*.mp4')) if DOWNLOADS_DIR.exists() else []
    log_files = list(LOGS_DIR.glob('*.log')) if LOGS_DIR.exists() else []
    db_size = DB_FILE.stat().st_size if DB_FILE.exists() else 0
    video_size = sum(file.stat().st_size for file in video_files) if video_files else 0
    log_size = sum(file.stat().st_size for file in log_files) if log_files else 0
    return {
        'video_count': len(video_files),
        'video_size': video_size,
        'log_count': len(log_files),
        'log_size': log_size,
        'db_size': db_size,
    }


def _render_summary() -> tuple[dict, dict]:
    status = get_system_status()
    space = _collect_space_summary()
    render_summary_metrics(
        [
            {'label': '视频占用', 'value': format_size(space['video_size'])},
            {'label': '日志占用', 'value': format_size(space['log_size'])},
            {'label': '数据库体积', 'value': format_size(space['db_size'])},
            {'label': '总存储占用', 'value': status['storage_usage']},
        ]
    )
    return status, space


def _render_space_cleanup(space: dict) -> None:
    with st.container(border=True):
        st.subheader('① 空间释放')
        st.caption('先回答磁盘空间主要被谁占用，再决定清理哪一块。')

        col1, col2 = st.columns(2)
        with col1:
            st.markdown('**本地视频文件**')
            st.caption(f"共 {space['video_count']} 个视频，占用 {format_size(space['video_size'])}")
            if render_danger_zone(
                '清理已删除视频的数据库记录',
                '同步本地文件和数据库状态，删除数据库中存在但本地已删除的视频记录。',
                '清理视频相关记录',
                'clean_db_video',
            ):
                with st.spinner('正在清理...'):
                    ok = _clean_deleted_videos()
                    if ok:
                        st.success('视频相关记录清理完成。')
                    else:
                        st.info('无需清理，数据库记录与本地文件一致。')

        with col2:
            st.markdown('**历史日志文件**')
            st.caption(f"共 {space['log_count']} 个日志，占用 {format_size(space['log_size'])}")
            if render_danger_zone(
                '清理 30 天前的旧日志',
                '自动删除 30 天前的历史日志文件，以释放磁盘空间。',
                '清理旧日志',
                'clean_logs',
            ):
                _clean_old_logs()
                st.success('旧日志清理完成。')


def _render_database_maintenance() -> None:
    with st.container(border=True):
        st.subheader('② 数据库维护')
        st.caption('数据库不只是一个文件体积问题，更是运行状态的一部分。')

        if not DB_FILE.exists():
            render_empty_state('数据库文件不存在。', '先运行一次主流程，系统会自动初始化数据库。', icon='🗄️')
            return

        st.info(f"数据库文件：`{DB_FILE.name}` ({format_size(DB_FILE.stat().st_size)})")
        db_stats = _get_db_stats()
        if db_stats:
            render_summary_metrics(
                [
                    {'label': '视频记录', 'value': db_stats['video_count']},
                    {'label': '来源记录', 'value': db_stats['user_count']},
                ]
            )

        if render_danger_zone(
            '清理过期数据库记录',
            '删除不再存在或无效的视频记录，减少历史脏数据。',
            '清理数据库记录',
            'clean_db_records',
        ):
            with st.spinner('正在清理数据库...'):
                cleaned, skipped = _clean_db_records()
                if cleaned > 0:
                    st.success(f'清理完成：已删除 {cleaned} 条记录，跳过 {skipped} 条。')
                else:
                    st.info('无需清理，数据库记录与本地文件一致。')


def _render_backup_restore() -> None:
    with st.container(border=True):
        st.subheader('③ 备份与恢复')
        st.caption('备份/恢复是最后一道保险，不应该和常规清理操作混在一起。')

        st.markdown(
            """
**备份内容包含：**
- `config/`
- `.auth/`
- `media_tools.db`
"""
        )

        col1, col2 = st.columns(2)
        with col1:
            st.markdown('**创建备份**')
            if st.button('📦 创建备份', type='primary', use_container_width=True):
                with st.spinner('正在创建备份...'):
                    ok, backup_path = _create_backup()
                    if ok:
                        st.success(f'✅ 备份已创建：{backup_path}')
                    else:
                        st.error('备份失败')

        with col2:
            st.markdown('**恢复备份**')
            uploaded = st.file_uploader('上传备份文件', type=['zip'])
            if uploaded and st.button('📥 恢复数据', type='secondary', use_container_width=True):
                st.warning('恢复操作将覆盖当前配置与数据库。确认无误后再执行。')
                if st.button('✅ 确认恢复', type='primary', use_container_width=True):
                    with st.spinner('正在恢复数据...'):
                        ok, msg = _restore_backup(uploaded)
                        if ok:
                            st.success(f'✅ {msg}')
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f'恢复失败：{msg}')


def _clean_deleted_videos() -> bool:
    try:
        from media_tools.douyin.core.cleaner import clean_deleted_videos

        deleted, _ = clean_deleted_videos(auto_confirm=True)
        return deleted > 0
    except Exception:
        logger.exception('清理已删除视频记录失败')
        return False


def _get_db_stats() -> dict | None:
    try:
        from media_tools.douyin.core.db_helper import execute_query

        video_count = execute_query('SELECT COUNT(*) FROM video_metadata')[0][0]
        user_count = execute_query('SELECT COUNT(*) FROM user_info_web')[0][0]
        return {'video_count': video_count, 'user_count': user_count}
    except Exception:
        logger.exception('获取数据库统计信息失败')
        return None


def _clean_db_records() -> tuple[int, int]:
    try:
        from media_tools.douyin.core.cleaner import clean_deleted_videos

        cleaned, skipped = clean_deleted_videos(auto_confirm=True)
        return cleaned, skipped
    except Exception as exc:
        logger.exception('清理数据库记录失败')
        st.error(f'清理失败: {exc}')
        return 0, 0


def _clean_old_logs() -> None:
    cutoff = time.time() - 30 * 24 * 3600
    for file in LOGS_DIR.glob('*.log'):
        if file.stat().st_mtime < cutoff:
            file.unlink()


def _restore_backup(uploaded_file) -> tuple[bool, str]:
    import shutil
    import tempfile
    import zipfile

    try:
        temp_dir = Path(tempfile.mkdtemp())
        zip_path = temp_dir / 'uploaded_backup.zip'
        with open(zip_path, 'wb') as file:
            file.write(uploaded_file.getbuffer())

        extract_dir = temp_dir / 'extracted'
        extract_dir.mkdir()
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        restored_items = []
        for item in ['config', '.auth', 'media_tools.db']:
            source_item = extract_dir / item
            target_item = PROJECT_ROOT / item
            if source_item.exists():
                if target_item.exists():
                    if target_item.is_dir():
                        shutil.rmtree(target_item)
                    else:
                        target_item.unlink()
                if source_item.is_dir():
                    shutil.copytree(source_item, target_item)
                else:
                    shutil.copy2(source_item, target_item)
                restored_items.append(item)

        shutil.rmtree(temp_dir)
        if not restored_items:
            return False, '备份文件中未找到有效的配置或数据目录。'
        return True, f"已成功恢复：{', '.join(restored_items)}。请重启应用以完全生效。"
    except zipfile.BadZipFile:
        return False, '上传的文件不是有效的 ZIP 压缩包。'
    except Exception as exc:
        logger.exception('恢复备份时发生异常')
        return False, str(exc)
    finally:
        if 'temp_dir' in locals() and temp_dir.exists():
            import shutil
            shutil.rmtree(temp_dir)


def _create_backup() -> tuple[bool, str]:
    import zipfile
    from datetime import datetime

    try:
        backup_dir = PROJECT_ROOT / 'backups'
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = backup_dir / f'media_tools_backup_{timestamp}.zip'
        items_to_backup = [('config', 'config'), ('.auth', '.auth'), ('media_tools.db', 'media_tools.db')]

        with zipfile.ZipFile(backup_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for item_path, arc_name in items_to_backup:
                path = PROJECT_ROOT / item_path
                if path.exists():
                    if path.is_file():
                        zipf.write(path, arc_name)
                    elif path.is_dir():
                        for file in path.rglob('*'):
                            if file.is_file():
                                zipf.write(file, f"{arc_name}/{file.relative_to(path)}")
        return True, str(backup_filename)
    except Exception as exc:
        logger.exception('创建备份失败')
        return False, str(exc)


render_page_header('🧹 清理与备份', '先看空间被谁占用，再决定清理；备份与恢复放在最后，作为保险动作。')
status, space = _render_summary()

_render_space_cleanup(space)
st.divider()
_render_database_maintenance()
st.divider()
_render_backup_restore()

if render_cta_section(
    '维护完成？',
    '返回工作台，继续处理当前阶段最重要的主流程。',
    '🏠 回到工作台',
    'go_home_from_cleanup',
):
    st.switch_page(get_page_path('home.py'))
