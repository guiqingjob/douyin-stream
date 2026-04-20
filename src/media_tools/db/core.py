import re
import sqlite3
import os
from pathlib import Path
from typing import Generator
from media_tools.logger import get_logger

logger = get_logger('db')

# --- Identifier validation ---
# 白名单：只允许字母、数字、下划线，首字符不能是数字
_IDENTIFIER_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')

# 硬编码的表名白名单（内部可信来源）
_VALID_TABLES = frozenset({
    'creators', 'media_assets', 'task_queue', 'auth_credentials',
    'Accounts_Pool', 'SystemSettings', 'scheduled_tasks', 'assets_fts'
})


def validate_identifier(name: str, field_name: str = "identifier") -> str:
    """
    校验标识符（表名、列名、索引名）安全性

    白名单正则：^[a-zA-Z_][a-zA-Z0-9_]*$

    Args:
        name: 要校验的标识符
        field_name: 字段名（用于错误信息）

    Returns:
        校验通过的标识符

    Raises:
        ValueError: 标识符包含非法字符
    """
    if not name or not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid {field_name}: {name!r} (must match ^[a-zA-Z_][a-zA-Z0-9_]*$)")
    return name


def _check_table_name(table: str) -> str:
    """校验表名，先检查硬编码白名单，再做通用校验"""
    if table in _VALID_TABLES:
        return table
    # 不在白名单中，做通用校验
    return validate_identifier(table, "table_name")


# --- Resolved DB path (set once at init, reused everywhere) ---
_db_path: str | None = None


def get_db_path() -> str:
    """Return the resolved DB path. Falls back to config_mgr if init_db hasn't been called."""
    global _db_path
    if _db_path is None:
        from media_tools.douyin.core.config_mgr import get_config
        _db_path = str(get_config().get_db_path())
    return _db_path


def _set_wal_mode(conn: sqlite3.Connection) -> None:
    """Set WAL mode if not already enabled (optimization to avoid repeated PRAGMA)."""
    try:
        cursor = conn.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()[0]
        if mode.upper() != "WAL":
            conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        conn.execute("PRAGMA journal_mode=WAL;")


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI dependency – yields a connection, always closes on exit."""
    conn = sqlite3.connect(get_db_path(), timeout=15.0)
    _set_wal_mode(conn)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


class DBConnection:
    """SQLite 连接封装，自动管理 WAL 模式和关闭"""

    _open_count = 0  # 打开的连接数（用于监控）
    _max_connections_warning = 20  # 超过此阈值警告

    def __init__(self, keep_open: bool = False):
        self._conn = sqlite3.connect(get_db_path(), timeout=15.0)
        self._keep_open = keep_open
        self._committed = False

        # 设置 WAL 模式
        _set_wal_mode(self._conn)
        self._conn.row_factory = sqlite3.Row

        # 监控连接数
        DBConnection._open_count += 1
        if DBConnection._open_count > DBConnection._max_connections_warning:
            logger.warning(f"DB connection count high: {DBConnection._open_count}")

    def __enter__(self) -> sqlite3.Connection:
        return self._conn

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """自动 commit/rollback + close"""
        DBConnection._open_count -= 1

        try:
            if exc_type is None and not self._committed:
                self._conn.commit()
            else:
                self._conn.rollback()
        except Exception:
            self._conn.rollback()
        finally:
            if not self._keep_open:
                self._conn.close()

    def commit(self) -> None:
        """显式提交（可选）"""
        self._conn.commit()
        self._committed = True

    @classmethod
    def get_stats(cls) -> dict:
        """返回连接统计"""
        return {"open_connections": cls._open_count, "max_warning": cls._max_connections_warning}


def get_db_connection(keep_open: bool = False) -> DBConnection:
    """
    获取数据库连接的上下文管理器

    用法:
        with get_db_connection() as conn:
            conn.execute(...)

    Args:
        keep_open: True 时不自动关闭连接（用于长事务场景）

    Returns:
        DBConnection 上下文管理器
    """
    return DBConnection(keep_open=keep_open)


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, column_def: str) -> None:
    """确保列存在，不存在则添加（带标识符校验）"""
    # 校验标识符安全
    safe_table = _check_table_name(table)
    safe_column = validate_identifier(column, "column_name")

    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({safe_table})")
    existing = {row[1] for row in cursor.fetchall()}
    if safe_column not in existing:
        cursor.execute(f"ALTER TABLE {safe_table} ADD COLUMN {safe_column} {column_def}")


def _ensure_fts_table(conn: sqlite3.Connection) -> None:
    """Create assets_fts FTS5 virtual table if it doesn't exist."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(assets_fts)")
    if cursor.fetchall():
        return  # Already exists
    cursor.execute("""
        CREATE VIRTUAL TABLE assets_fts USING fts5(
            asset_id UNINDEXED,
            title,
            transcript_text,
            tokenize='unicode61 remove_diacritics 2'
        )
    """)


def ensure_fts_populated() -> bool:
    """Ensure FTS5 index has data; rebuilds from media_assets if empty. Returns True if populated."""
    with get_db_connection() as conn:
        cur = conn.execute("SELECT COUNT(*) FROM assets_fts")
        count = cur.fetchone()[0]
        if count > 0:
            return True
        _ensure_fts_table(conn)
        _rebuild_fts_from_assets(conn)
        return True


def update_fts_for_asset(asset_id: str, title: str, transcript_text: str) -> None:
    """Upsert a single asset into the FTS5 index."""
    with get_db_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO assets_fts(asset_id, title, transcript_text) VALUES (?, ?, ?)",
            (asset_id, title, transcript_text or ""),
        )


def _rebuild_fts_from_assets(conn: sqlite3.Connection) -> int:
    """Rebuild full FTS5 index from media_assets. Caller must hold conn."""
    cursor = conn.execute(
        "SELECT asset_id, title, COALESCE(transcript_text, '') FROM media_assets"
    )
    rows = list(cursor.fetchall())
    if not rows:
        return 0
    conn.executemany(
        "INSERT OR REPLACE INTO assets_fts(asset_id, title, transcript_text) VALUES (?, ?, ?)",
        rows,
    )
    conn.commit()
    return len(rows)


def rebuild_fts_index() -> int:
    """Full rebuild of FTS5 index. Returns row count."""
    with get_db_connection() as conn:
        _ensure_fts_table(conn)
        count = _rebuild_fts_from_assets(conn)
        logger.info(f"FTS5 index rebuilt: {count} rows")
        return count

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
            homepage_url TEXT,
            platform TEXT DEFAULT 'douyin',
            sync_status TEXT DEFAULT 'active',
            last_fetch_time DATETIME
        )
        """)

        # 迁移：为已存在的表添加 homepage_url 字段
        try:
            cursor.execute("ALTER TABLE creators ADD COLUMN homepage_url TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # 字段已存在

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
        _ensure_column(conn, "task_queue", "cancel_requested", "INTEGER DEFAULT 0")
        _ensure_column(conn, "task_queue", "auto_retry", "INTEGER DEFAULT 0")
        _ensure_column(conn, "creators", "platform", "TEXT DEFAULT 'douyin'")
        _ensure_column(conn, "creators", "sync_status", "TEXT DEFAULT 'active'")
        _ensure_column(conn, "creators", "last_fetch_time", "DATETIME")
        _ensure_column(conn, "creators", "avatar", "TEXT")
        _ensure_column(conn, "creators", "bio", "TEXT")
        _ensure_column(conn, "Accounts_Pool", "remark", "TEXT DEFAULT ''")
        _ensure_column(conn, "Accounts_Pool", "auth_state_path", "TEXT DEFAULT ''")
        _ensure_column(conn, "media_assets", "source_url", "TEXT")
        _ensure_column(conn, "media_assets", "is_read", "BOOLEAN DEFAULT 0")
        _ensure_column(conn, "media_assets", "is_starred", "BOOLEAN DEFAULT 0")
        _ensure_column(conn, "media_assets", "folder_path", "TEXT DEFAULT ''")
        _ensure_column(conn, "media_assets", "create_time", "DATETIME")
        _ensure_column(conn, "media_assets", "update_time", "DATETIME")
        _ensure_column(conn, "media_assets", "transcript_preview", "TEXT")
        _ensure_column(conn, "media_assets", "transcript_text", "TEXT")

        # FTS5 全文索引（用于素材搜索加速）
        _ensure_fts_table(conn)

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
