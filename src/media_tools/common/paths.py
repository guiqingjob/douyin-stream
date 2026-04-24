"""Common path utilities — neutral layer to eliminate cross-domain imports."""
from __future__ import annotations

from pathlib import Path


def get_project_root() -> Path:
    """Return the project root directory."""
    from media_tools.douyin.core.config_mgr import get_config

    return get_config().project_root


def get_download_path() -> Path:
    """Return the downloads directory path."""
    from media_tools.douyin.core.config_mgr import get_config

    return get_config().get_download_path()


def get_db_path() -> Path:
    """Return the SQLite database file path."""
    from media_tools.douyin.core.config_mgr import get_config

    return get_config().get_db_path()
