import sqlite3
import os
from pathlib import Path
from media_tools.logger import get_logger

logger = get_logger('db')

def init_db(db_path: str | Path):
    """
    初始化 V2 架构所需的数据表
    
    Args:
        db_path: 数据库文件路径 (通常为 media_tools.db)
    """
    db_path = Path(db_path)
    
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
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 1. 创作者域 (Creator Domain)
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS creators (
            uid TEXT PRIMARY KEY,
            sec_user_id TEXT,
            nickname TEXT,
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
        
        # 创建索引优化查询
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_media_assets_creator ON media_assets(creator_uid)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_media_assets_video_status ON media_assets(video_status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_media_assets_transcript_status ON media_assets(transcript_status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_queue_status ON task_queue(status)")
        
        conn.commit()
        logger.info("V2 架构数据库初始化完成")
    except Exception as e:
        logger.error(f"初始化数据库失败: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    # 测试执行
    import sys
    db_path = "media_tools.db"
    init_db(db_path)
    print("DB Init success")
