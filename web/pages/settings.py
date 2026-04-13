"""
系统配置页面
"""

from pathlib import Path

import streamlit as st

from web.constants import PROJECT_ROOT, QWEN_AUTH_PATH


# render_settings
"""渲染系统配置页面"""
st.title("⚙️ 系统配置")
st.caption("先做环境检测，再处理备份修复和预设应用。")

tab1, tab2, tab3 = st.tabs(["🔍 环境检测", "💾 配置管理", "📋 预设模板"])

with tab1:
    _render_env_check()
with tab2:
    _render_config_management()
with tab3:
    _render_presets()


def _render_env_check() -> None:
    """环境检测"""
    st.subheader("🔍 环境检测")
    st.caption("建议首次使用时先完整跑一次，确认下载和转写链路可用。")

    if st.button("运行完整检测", type="primary"):
        with st.spinner("正在检测..."):
            _run_env_check()


def _run_env_check() -> None:
    """运行环境检测"""
    try:
        checks = [
            ("Python 版本", _check_python_version),
            ("f2 包", lambda: _check_package("f2")),
            ("playwright 包", lambda: _check_package("playwright")),
            ("ffmpeg", _check_ffmpeg),
        ]

        for name, func in checks:
            ok, msg = func()
            if ok:
                st.success(f"✅ {name}: {msg}")
            else:
                st.error(f"❌ {name}: {msg}")

        douyin_auth = _check_douyin_auth()
        if douyin_auth:
            st.success("✅ 抖音 Cookie: 已配置")
        else:
            st.warning("⚠️ 抖音 Cookie: 未配置")

        qwen_auth = _check_qwen_auth()
        if qwen_auth:
            st.success("✅ Qwen 认证: 已配置")
        else:
            st.warning("⚠️ Qwen 认证: 未配置")

    except Exception as e:
        st.error(f"检测失败: {e}")


def _render_config_management() -> None:
    """配置管理"""
    st.subheader("💾 配置管理")
    st.caption("这里用于备份配置、修复常见问题。")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**备份**")
        if st.button("创建配置备份", use_container_width=True):
            backup_path = _backup_configs()
            if backup_path:
                st.success(f"备份成功: {backup_path}")
            else:
                st.error("备份失败")

    with col2:
        st.markdown("**修复**")
        if st.button("自动修复常见问题", use_container_width=True):
            _fix_common_issues()
            st.success("修复完成")


def _render_presets() -> None:
    """预设模板"""
    st.subheader("📋 预设模板")
    st.caption("适合快速切换新手 / 专业 / 服务器场景。")

    presets = _load_presets()

    if not presets:
        st.info("未配置预设模板")
        return

    preset_options = {v["label"]: k for k, v in presets.items()}
    selected_label = st.radio("选择预设", list(preset_options.keys()), index=0)
    preset_key = preset_options[selected_label]

    if st.button("应用预设", type="primary"):
        ok = _apply_preset(preset_key)
        if ok:
            st.success(f"已应用预设: {selected_label}")
        else:
            st.error("应用失败")


def _load_presets() -> dict:
    """从配置文件加载预设模板"""
    import yaml

    default_presets = {
        "beginner": {"label": "🌱 新手模式 - 最简配置"},
        "pro": {"label": "🚀 专业模式 - 全部功能"},
        "server": {"label": "🖥️ 服务器模式 - 后台运行"},
    }

    from web.constants import PROJECT_ROOT

    config_path = PROJECT_ROOT / "config" / "config.yaml"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            if "presets" in config:
                for key, preset in config["presets"].items():
                    if "label" not in preset:
                        preset["label"] = default_presets.get(key, {}).get("label", key)
                return {**default_presets, **config["presets"]}
        except Exception:
            pass

    return default_presets


def _check_python_version() -> tuple[bool, str]:
    """检查 Python 版本"""
    import sys

    version = sys.version_info
    ver_str = f"{version.major}.{version.minor}.{version.micro}"
    return True, f"Python {ver_str}"


def _check_package(name: str) -> tuple[bool, str]:
    """检查包是否安装"""
    try:
        import importlib

        importlib.import_module(name)
        return True, "已安装"
    except ImportError:
        return False, "未安装"


def _check_ffmpeg() -> tuple[bool, str]:
    """检查 ffmpeg"""
    import subprocess

    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        if result.returncode == 0:
            return True, "已安装"
        return False, "未安装"
    except FileNotFoundError:
        return False, "未安装"


def _check_douyin_auth() -> bool:
    """检查抖音认证"""
    try:
        from media_tools.douyin.core.config_mgr import get_config

        return get_config().has_cookie()
    except Exception:
        return False


def _check_qwen_auth() -> bool:
    """检查 Qwen 认证"""
    return QWEN_AUTH_PATH.exists() and QWEN_AUTH_PATH.stat().st_size > 1000


def _backup_configs() -> str | None:
    """备份配置"""
    try:
        from media_tools.config_manager import ConfigManager

        mgr = ConfigManager()
        backup_path = mgr.backup_configs()
        return str(backup_path)
    except Exception:
        return None


def _fix_common_issues() -> None:
    """修复常见问题"""
    try:
        from media_tools.config_manager import ConfigManager

        mgr = ConfigManager()
        mgr.fix_common_issues()
    except Exception:
        pass


def _apply_preset(preset_name: str) -> bool:
    """应用预设"""
    try:
        from media_tools.config_presets import apply_preset

        return apply_preset(preset_name, auto_apply=True)
    except Exception:
        return False
