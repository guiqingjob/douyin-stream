"""
Web 管理面板常量定义
统一管理路径、页面标签和公共配置
"""

from pathlib import Path

from media_tools.logger import get_logger
logger = get_logger('web')


# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent

# 认证路径
QWEN_AUTH_PATH = PROJECT_ROOT / ".auth" / "qwen-storage-state.json"
DOUYIN_COOKIE_PATH = PROJECT_ROOT / ".auth" / "douyin-cookie.json"

# 数据目录
TEMP_UPLOADS_DIR = PROJECT_ROOT / "temp_uploads"
DOWNLOADS_DIR = PROJECT_ROOT / "downloads"
TRANSCRIPTS_DIR = PROJECT_ROOT / "transcripts"
LOGS_DIR = PROJECT_ROOT / "logs"

# 任务状态文件
TASK_STATE_FILE = PROJECT_ROOT / ".task_state.json"

# 数据库文件
DB_FILE = PROJECT_ROOT / "douyin_users.db"

# 页面标签
PAGE_HOME = "🏠 工作台"
PAGE_DOWNLOAD = "📥 下载中心"
PAGE_TRANSCRIBE = "🎙️ 转写中心"
PAGE_FOLLOWING = "👥 关注管理"
PAGE_ACCOUNTS = "🔑 账号与配额"
PAGE_CLEANUP = "🗑️ 清理与备份"
PAGE_SETTINGS = "⚙️ 系统配置"

NAV_PAGES = [
    PAGE_HOME,
    PAGE_DOWNLOAD,
    PAGE_TRANSCRIBE,
    PAGE_FOLLOWING,
    PAGE_ACCOUNTS,
    PAGE_CLEANUP,
    PAGE_SETTINGS,
]
