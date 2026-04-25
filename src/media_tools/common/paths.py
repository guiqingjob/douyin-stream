"""Common path utilities — 委托给统一配置系统。"""
from __future__ import annotations

from pathlib import Path


def get_project_root() -> Path:
    """Return the project root directory."""
    from media_tools.core.config import get_project_root as _get_project_root
    return _get_project_root()


def get_download_path() -> Path:
    """Return the downloads directory path."""
    from media_tools.core.config import get_download_path as _get_download_path
    return _get_download_path()


def get_db_path() -> Path:
    """Return the SQLite database file path."""
    from media_tools.core.config import get_db_path as _get_db_path
    return _get_db_path()
