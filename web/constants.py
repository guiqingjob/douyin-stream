"""
Web 管理面板常量定义
统一管理硬编码路径和配置值
"""

from pathlib import Path

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
