"""
系统配置页面
"""

from __future__ import annotations

import streamlit as st

from media_tools.logger import get_logger
from media_tools.transcribe.auth_state import has_qwen_auth_state
from media_tools.web.components.ui_patterns import render_cta_section, render_page_header, render_summary_metrics
from media_tools.web.constants import PROJECT_ROOT
from media_tools.web.services.status import get_system_status
from media_tools.web.utils import get_page_path

logger = get_logger('web')

_ENV_REPORT_KEY = '_settings_env_report'
_REPAIR_RESULT_KEY = '_settings_repair_result'


def _check_python_version() -> tuple[bool, str]:
    import sys

    version = sys.version_info
    return True, f'Python {version.major}.{version.minor}.{version.micro}'


def _check_package(name: str) -> tuple[bool, str]:
    try:
        import importlib

        importlib.import_module(name)
        return True, '已安装'
    except ImportError:
        return False, '未安装'


def _check_ffmpeg() -> tuple[bool, str]:
    import subprocess

    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            return True, '已安装'
        return False, '未安装'
    except FileNotFoundError:
        return False, '未安装'


def _check_douyin_auth() -> tuple[bool, str]:
    try:
        from media_tools.douyin.core.config_mgr import get_config

        ok = get_config().has_cookie()
        return ok, '已配置 Cookie' if ok else '未配置 Cookie'
    except Exception as exc:
        logger.exception('检查抖音认证失败')
        return False, str(exc)


def _check_qwen_auth() -> tuple[bool, str]:
    try:
        ok = has_qwen_auth_state()
        return ok, '已检测到认证状态' if ok else '未检测到认证状态'
    except Exception as exc:
        logger.exception('检查 Qwen 认证失败')
        return False, str(exc)


def _collect_env_report() -> dict:
    report_items: list[dict] = []

    try:
        from media_tools.douyin.core.env_check import check_all

        passed, details = check_all()
        for name, info in (details or {}).items():
            report_items.append(
                {
                    'name': name,
                    'ok': bool(info.get('ok')),
                    'message': info.get('message', ''),
                }
            )
    except Exception as exc:
        logger.exception('运行完整环境检测失败，回退到基础检测')
        fallback_checks = [
            ('Python 版本', _check_python_version),
            ('f2 包', lambda: _check_package('f2')),
            ('playwright 包', lambda: _check_package('playwright')),
            ('ffmpeg', _check_ffmpeg),
        ]
        for name, func in fallback_checks:
            ok, msg = func()
            report_items.append({'name': name, 'ok': ok, 'message': msg})
        passed = all(item['ok'] for item in report_items)
        report_items.append({'name': '完整检测回退', 'ok': False, 'message': str(exc)})

    for name, func in [('抖音认证', _check_douyin_auth), ('Qwen 认证', _check_qwen_auth)]:
        ok, msg = func()
        report_items.append({'name': name, 'ok': ok, 'message': msg})

    total = len(report_items)
    passed_count = sum(1 for item in report_items if item['ok'])
    return {
        'passed': passed and all(item['ok'] for item in report_items),
        'items': report_items,
        'passed_count': passed_count,
        'failed_count': total - passed_count,
    }


def _render_summary() -> dict:
    status = get_system_status()
    render_summary_metrics(
        [
            {'label': '环境状态', 'value': '正常' if status['env_ok'] else '待检查'},
            {'label': '下载认证', 'value': '已就绪' if status['cookie_ok'] else '待配置'},
            {'label': '转写认证', 'value': '已就绪' if status['qwen_ok'] else '待配置'},
            {'label': '当前阶段', 'value': status['workflow_stage']},
        ]
    )
    return status


def _render_env_center() -> None:
    with st.container(border=True):
        st.subheader('① 环境可用性检查')
        st.caption('这页首先要回答：当前环境能不能稳定跑通下载和转写。')
        st.caption(f'项目根目录：`{PROJECT_ROOT}`')

        if st.button('运行完整检测', type='primary', use_container_width=True):
            with st.spinner('正在检测...'):
                st.session_state[_ENV_REPORT_KEY] = _collect_env_report()

        report = st.session_state.get(_ENV_REPORT_KEY)
        if not report:
            st.info('尚未运行完整检测。建议先跑一次，确认依赖、工具链和认证状态都正常。')
            return

        render_summary_metrics(
            [
                {'label': '通过项', 'value': report['passed_count']},
                {'label': '异常项', 'value': report['failed_count']},
                {'label': '总状态', 'value': '通过' if report['passed'] else '需处理'},
            ]
        )

        for item in report['items']:
            if item['ok']:
                st.success(f"✅ {item['name']}: {item['message']}")
            else:
                if '认证' in item['name']:
                    st.warning(f"⚠️ {item['name']}: {item['message']}")
                else:
                    st.error(f"❌ {item['name']}: {item['message']}")


def _render_repair_center() -> None:
    with st.container(border=True):
        st.subheader('② 修复与配置备份')
        st.caption('修复动作和配置备份放在一起，因为它们都属于“先保底，再修复”的系统维护流程。')

        col1, col2 = st.columns(2)
        with col1:
            st.markdown('**创建配置备份**')
            st.caption('在大改配置前，先留一个可回滚的快照。')
            if st.button('创建配置备份', use_container_width=True):
                backup_path = _backup_configs()
                if backup_path:
                    st.session_state[_REPAIR_RESULT_KEY] = ('success', f'备份成功：{backup_path}')
                else:
                    st.session_state[_REPAIR_RESULT_KEY] = ('error', '备份失败')
                st.rerun()

        with col2:
            st.markdown('**自动修复常见问题**')
            st.caption('适合在路径变更、配置残缺或首次迁移后执行一次。')
            if st.button('自动修复常见问题', use_container_width=True):
                ok = _fix_common_issues()
                if ok:
                    st.session_state[_REPAIR_RESULT_KEY] = ('success', '自动修复已完成')
                else:
                    st.session_state[_REPAIR_RESULT_KEY] = ('warning', '修复流程已执行，请检查日志确认结果')
                st.rerun()

        result = st.session_state.get(_REPAIR_RESULT_KEY)
        if result:
            level, message = result
            if level == 'success':
                st.success(message)
            elif level == 'warning':
                st.warning(message)
            else:
                st.error(message)


def _load_presets() -> dict:
    import yaml

    default_presets = {
        'beginner': {
            'label': '🌱 新手模式',
            'description': '尽量保守，适合第一次跑通链路。',
        },
        'pro': {
            'label': '🚀 专业模式',
            'description': '打开更多能力，适合高频使用。',
        },
        'server': {
            'label': '🖥️ 服务器模式',
            'description': '偏向后台执行与长期运行。',
        },
    }

    config_path = PROJECT_ROOT / 'config' / 'config.yaml'
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
            if 'presets' in config:
                merged = dict(default_presets)
                for key, preset in config['presets'].items():
                    merged[key] = {
                        'label': preset.get('label', default_presets.get(key, {}).get('label', key)),
                        'description': preset.get('description', default_presets.get(key, {}).get('description', '')),
                    }
                return merged
        except Exception:
            logger.exception('加载预设模板失败')
    return default_presets


def _render_presets() -> None:
    with st.container(border=True):
        st.subheader('③ 预设模板')
        st.caption('预设不是装饰，它的作用是快速切换系统运行风格，减少手动配置成本。')

        presets = _load_presets()
        if not presets:
            st.info('未配置预设模板。')
            return

        preset_options = {value['label']: key for key, value in presets.items()}
        selected_label = st.radio('选择预设', list(preset_options.keys()), index=0)
        preset_key = preset_options[selected_label]
        selected_preset = presets[preset_key]

        if selected_preset.get('description'):
            st.info(selected_preset['description'])

        if st.button('应用预设', type='primary', use_container_width=True):
            ok = _apply_preset(preset_key)
            if ok:
                st.success(f'已应用预设：{selected_label}')
            else:
                st.error('应用失败，请检查相关配置模块。')


def _backup_configs() -> str | None:
    try:
        from media_tools.config_manager import ConfigManager

        mgr = ConfigManager()
        backup_path = mgr.backup_configs()
        return str(backup_path)
    except Exception:
        logger.exception('创建配置备份失败')
        return None


def _fix_common_issues() -> bool:
    try:
        from media_tools.config_manager import ConfigManager

        mgr = ConfigManager()
        mgr.fix_common_issues()
        return True
    except Exception:
        logger.exception('自动修复常见问题失败')
        return False


def _apply_preset(preset_name: str) -> bool:
    try:
        from media_tools.config_presets import apply_preset

        return apply_preset(preset_name, auto_apply=True)
    except Exception:
        logger.exception('应用预设失败')
        return False


render_page_header('⚙️ 系统配置', '先确认系统可用性，再做修复与预设切换，避免把维护动作和业务流程混在一起。')
status = _render_summary()

_render_env_center()
st.divider()
_render_repair_center()
st.divider()
_render_presets()

if (not status['cookie_ok'] or not status['qwen_ok']) and render_cta_section(
    '还缺认证？',
    '前往账号与认证页面，补齐下载或转写所需的授权状态。',
    '🔑 去账号与认证',
    'go_accounts_from_settings',
):
    st.switch_page(get_page_path('accounts.py'))
elif render_cta_section(
    '维护完成？',
    '返回工作台，继续按当前阶段推进主流程。',
    '🏠 回到工作台',
    'go_home_from_settings',
):
    st.switch_page(get_page_path('home.py'))
