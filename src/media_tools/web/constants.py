"""
Web 管理面板常量定义
统一管理路径和公共配置
"""

from media_tools.douyin.core.config_mgr import get_config


PROJECT_ROOT = get_config().project_root

QWEN_AUTH_PATH = PROJECT_ROOT / '.auth' / 'qwen-storage-state.json'
DOUYIN_COOKIE_PATH = PROJECT_ROOT / '.auth' / 'douyin-cookie.json'

TEMP_UPLOADS_DIR = PROJECT_ROOT / 'temp_uploads'
DOWNLOADS_DIR = PROJECT_ROOT / 'downloads'
TRANSCRIPTS_DIR = PROJECT_ROOT / 'transcripts'
LOGS_DIR = PROJECT_ROOT / 'logs'

DB_FILE = PROJECT_ROOT / 'media_tools.db'
