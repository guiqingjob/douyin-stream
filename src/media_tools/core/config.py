"""统一配置系统 — 数据库 SystemSettings 是运行时配置的唯一事实源。

配置项归属：
- SystemSettings 表：auto_transcribe, auto_delete, concurrency, api_key（运行时用户可修改）
- config/config.yaml：cookie, download_path, naming（启动时确定，cookie 暂不迁移到数据库）
- 环境变量：PIPELINE_* 系列（启动参数）
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

from media_tools.db.core import get_db_connection, validate_identifier


class ConfigError(Exception):
    """配置错误"""


# --- Runtime config backed by SystemSettings ---

_RUNTIME_DEFAULTS: dict[str, str] = {
    "concurrency": "5",
    "auto_transcribe": "false",
    "auto_delete": "true",
    "api_key": "",
}


def _get_system_setting(key: str) -> str | None:
    """从 SystemSettings 表读取单个配置值。"""
    try:
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT value FROM SystemSettings WHERE key = ?", (key,)
            ).fetchone()
            return row[0] if row else None
    except (sqlite3.Error, OSError):
        return None


def _set_system_setting(key: str, value: str) -> None:
    """写入 SystemSettings 表。"""
    try:
        with get_db_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO SystemSettings (key, value) VALUES (?, ?)",
                (key, value),
            )
            conn.commit()
    except (sqlite3.Error, OSError) as e:
        raise ConfigError(f"无法保存配置 {key}: {e}") from e


def get_runtime_setting(key: str, default: str | None = None) -> str:
    """读取运行时配置。优先从 SystemSettings 读取，fallback 到默认值。"""
    value = _get_system_setting(key)
    if value is not None:
        return value
    return default if default is not None else _RUNTIME_DEFAULTS.get(key, "")


def get_runtime_setting_bool(key: str, default: bool = False) -> bool:
    """读取布尔型运行时配置。"""
    raw = get_runtime_setting(key)
    if raw == "":
        return default
    return raw.lower() in ("true", "1", "yes", "on")


def get_runtime_setting_int(key: str, default: int = 0) -> int:
    """读取整型运行时配置。"""
    raw = get_runtime_setting(key)
    if raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def set_runtime_setting(key: str, value: str | bool | int) -> None:
    """设置运行时配置，写入 SystemSettings 表。"""
    if isinstance(value, bool):
        str_value = "true" if value else "false"
    else:
        str_value = str(value)
    _set_system_setting(key, str_value)


# --- Config.yaml access (read-only for runtime) ---

_CONFIG_MGR: Any | None = None


def _get_config_mgr() -> Any:
    """延迟加载 douyin 配置管理器（兼容层）。"""
    global _CONFIG_MGR
    if _CONFIG_MGR is None:
        from media_tools.douyin.core.config_mgr import get_config

        _CONFIG_MGR = get_config()
    return _CONFIG_MGR


def reset_config_cache() -> None:
    """重置配置缓存（测试用）。"""
    global _CONFIG_MGR
    _CONFIG_MGR = None


def get_cookie() -> str:
    """获取 Cookie 字符串。来源：config.yaml（敏感信息暂不迁移到数据库）。"""
    return _get_config_mgr().get_cookie()


def has_cookie() -> bool:
    """检查是否配置了 Cookie。"""
    return _get_config_mgr().has_cookie()


def get_download_path() -> Path:
    """获取下载路径。来源：config.yaml。"""
    return _get_config_mgr().get_download_path()


def get_naming_format() -> str:
    """获取文件命名格式。来源：config.yaml。"""
    return _get_config_mgr().get_naming()


def get_project_root() -> Path:
    """获取项目根目录。来源：config.yaml。"""
    return _get_config_mgr().project_root


def get_db_path() -> Path:
    """获取数据库文件路径。来源：config.yaml。"""
    return _get_config_mgr().get_db_path()


# --- Unified convenience API ---

class AppConfig:
    """统一应用配置接口 — 所有配置项的唯一入口。"""

    # Runtime settings (SystemSettings)
    @property
    def concurrency(self) -> int:
        return get_runtime_setting_int("concurrency", 5)

    @property
    def auto_transcribe(self) -> bool:
        return get_runtime_setting_bool("auto_transcribe", False)

    @property
    def auto_delete(self) -> bool:
        return get_runtime_setting_bool("auto_delete", True)

    @property
    def api_key(self) -> str:
        return get_runtime_setting("api_key", "")

    # Static settings (config.yaml)
    @property
    def cookie(self) -> str:
        return get_cookie()

    @property
    def download_path(self) -> Path:
        return get_download_path()

    @property
    def naming_format(self) -> str:
        return get_naming_format()

    @property
    def project_root(self) -> Path:
        return get_project_root()

    @property
    def db_path(self) -> Path:
        return get_db_path()


# 全局 AppConfig 实例（轻量，无状态缓存）
_app_config = AppConfig()


def get_app_config() -> AppConfig:
    """获取全局 AppConfig 实例。"""
    return _app_config


# --- Pipeline config from env vars (unchanged, startup params) ---


def _safe_int_env(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except (TypeError, ValueError):
        return default


class PipelineConfig:
    """Pipeline 配置 — 从环境变量读取（启动参数），支持实例化覆盖。"""

    def __init__(
        self,
        export_format: str = "",
        output_dir: str = "",
        delete_after_export: bool | None = None,
        account_id: str = "",
        remove_video: bool | None = None,
        keep_original: bool | None = None,
        concurrency: int | None = None,
    ):
        self._export_format = export_format
        self._output_dir = output_dir
        self._delete_after_export = delete_after_export
        self._account_id = account_id
        self._remove_video = remove_video
        self._keep_original = keep_original
        self._concurrency = concurrency

    @property
    def export_format(self) -> str:
        if self._export_format:
            return self._export_format
        return os.environ.get("PIPELINE_EXPORT_FORMAT", "md").strip().lower()

    @property
    def output_dir(self) -> str:
        if self._output_dir:
            return self._output_dir
        return os.environ.get("PIPELINE_OUTPUT_DIR", str(get_project_root() / "transcripts")).strip()

    @property
    def output_path(self) -> Path:
        if self._output_dir:
            return Path(self._output_dir).resolve()
        return Path(self.output_dir).resolve()

    @property
    def delete_after_export(self) -> bool:
        if self._delete_after_export is not None:
            return self._delete_after_export
        return os.environ.get("PIPELINE_DELETE_AFTER_EXPORT", "true").lower() == "true"

    @property
    def account_id(self) -> str:
        if self._account_id:
            return self._account_id
        return os.environ.get("PIPELINE_ACCOUNT_ID", "").strip()

    @property
    def remove_video(self) -> bool:
        if self._remove_video is not None:
            return self._remove_video
        return os.environ.get("PIPELINE_REMOVE_VIDEO", "false").lower() == "true"

    @property
    def keep_original(self) -> bool:
        if self._keep_original is not None:
            return self._keep_original
        return os.environ.get("PIPELINE_KEEP_ORIGINAL", "true").lower() == "true"

    @property
    def concurrency(self) -> int:
        if self._concurrency is not None:
            return self._concurrency
        return _safe_int_env("PIPELINE_CONCURRENCY", 5)


_pipeline_config = PipelineConfig()


def get_pipeline_config() -> PipelineConfig:
    """获取全局 PipelineConfig 实例。"""
    return _pipeline_config
