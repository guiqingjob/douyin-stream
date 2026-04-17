import sqlite3
import os
from pathlib import Path
from typing import Generator
from media_tools.logger import get_logger

logger = get_logger('db')

# --- Resolved DB path (set once at init, reused everywhere) ---
_db_path: str | None = None


def get_db_path() -> str:
    """Return the resolved DB path. Falls back to config_mgr if init_db hasn't been called."""
    global _db_path
    if _db_path is None:
        from media_tools.douyin.core.config_mgr import get_config
        _db_path = str(get_config().get_db_path())
    return _db_path


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI dependency – yields a connection, always closes on exit."""
    conn = sqlite3.connect(get_db_path(), timeout=15.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def get_db_connection() -> sqlite3.Connection:
    """Non-generator helper for background tasks / non-FastAPI contexts."""
    conn = sqlite3.connect(get_db_path(), timeout=15.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, column_def: str) -> None:
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cursor.fetchall()}
    if column not in existing:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_def}")

def init_db(db_path: str | Path):
    """
    初始化所有数据表（启动时调用一次）

    Args:
        db_path: 数据库文件路径 (通常为 media_tools.db)
    """
    global _db_path
    db_path = Path(db_path)
    _db_path = str(db_path)

    # 兼容性处理：如果旧版 douyin_users.db 存在且新版不存在，自动重命名
    old_db_path = db_path.parent / "douyin_users.db"
    if old_db_path.exists() and not db_path.exists():
        try:
            logger.info(f"发现旧版数据库 {old_db_path.name}，正在迁移至 {db_path.name}...")
            os.rename(old_db_path, db_path)
        except Exception as e:
            logger.error(f"重命名旧版数据库失败: {e}")

    # 确保父目录存在
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = None
    try:
        conn = sqlite3.connect(str(db_path), timeout=15.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()

        # 1. 创作者域 (Creator Domain)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS creators (
            uid TEXT PRIMARY KEY,
            sec_user_id TEXT,
            nickname TEXT,
            avatar TEXT,
            bio TEXT,
            platform TEXT DEFAULT 'douyin',
            sync_status TEXT DEFAULT 'active',
            last_fetch_time DATETIME
        )
        """)

        # 2. 资产域 (Asset Domain)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS media_assets (
            asset_id TEXT PRIMARY KEY,
            creator_uid TEXT,
            source_url TEXT,
            title TEXT,
            duration INTEGER,

            video_path TEXT,
            video_status TEXT DEFAULT 'pending',

            transcript_path TEXT,
            transcript_status TEXT DEFAULT 'none',

            create_time DATETIME,
            update_time DATETIME
        )
        """)

        # 3. 任务域 (Task Domain)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_queue (
            task_id TEXT PRIMARY KEY,
            task_type TEXT,
            payload JSON,
            status TEXT DEFAULT 'PENDING',
            progress REAL DEFAULT 0.0,
            error_msg TEXT,
            create_time DATETIME,
            update_time DATETIME,
            start_time DATETIME,
            end_time DATETIME
        )
        """)

        # 4. 认证域 (Auth Domain)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS auth_credentials (
            platform TEXT PRIMARY KEY,
            auth_data JSON,
            is_valid BOOLEAN DEFAULT 1,
            last_check_time DATETIME
        )
        """)

        # 5. 账号池 (Account Pool) — 原散落在 settings.py / f2_helper.py
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS Accounts_Pool (
            account_id TEXT PRIMARY KEY,
            platform TEXT,
            cookie_data TEXT,
            status TEXT DEFAULT 'active',
            last_used TIMESTAMP,
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 6. 系统设置 (System Settings) — 原散落在 settings.py
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS SystemSettings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """)

        # 7. 定时任务 (Scheduled Tasks) — 原散落在 scheduler.py
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_tasks (
            task_id TEXT PRIMARY KEY,
            task_type TEXT,
            cron_expr TEXT,
            enabled BOOLEAN DEFAULT 1,
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # 创建索引优化查询
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_media_assets_creator ON media_assets(creator_uid)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_media_assets_video_status ON media_assets(video_status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_media_assets_transcript_status ON media_assets(transcript_status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_queue_status ON task_queue(status)")

        _ensure_column(conn, "task_queue", "update_time", "DATETIME")
        _ensure_column(conn, "creators", "avatar", "TEXT")
        _ensure_column(conn, "creators", "bio", "TEXT")
        _ensure_column(conn, "Accounts_Pool", "remark", "TEXT DEFAULT ''")
        _ensure_column(conn, "Accounts_Pool", "auth_state_path", "TEXT DEFAULT ''")
        _ensure_column(conn, "media_assets", "is_read", "BOOLEAN DEFAULT 0")
        _ensure_column(conn, "media_assets", "is_starred", "BOOLEAN DEFAULT 0")
        _ensure_column(conn, "media_assets", "folder_path", "TEXT DEFAULT ''")
        _ensure_column(conn, "media_assets", "create_time", "DATETIME")
        _ensure_column(conn, "media_assets", "update_time", "DATETIME")

        conn.commit()
        logger.info("数据库初始化完成（含全部 7 张表）")
    except Exception as e:
        logger.error(f"初始化数据库失败: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    db_path = "media_tools.db"
    init_db(db_path)
    print("DB Init success")
