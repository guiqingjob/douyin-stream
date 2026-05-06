"""带缓存的系统设置访问层

对热点数据（如系统设置）增加内存缓存，减少数据库访问次数，
提升响应速度。
"""
import time
from media_tools.db.core import get_db_connection
from media_tools.logger import get_logger

logger = get_logger(__name__)


class CachedSystemSettings:
    """带缓存的系统设置访问层"""

    _cache: dict[str, tuple[str, float]] = {}  # key -> (value, expire_time)
    _default_ttl: int = 300  # 5分钟缓存过期时间
    _cache_lock = __import__('threading').Lock()

    @staticmethod
    def get(key: str, default: str = "") -> str:
        """获取设置（带缓存）
        
        Args:
            key: 设置键名
            default: 默认值
            
        Returns:
            设置值
        """
        now = time.time()
        
        # 先检查缓存
        with CachedSystemSettings._cache_lock:
            if key in CachedSystemSettings._cache:
                value, expire_time = CachedSystemSettings._cache[key]
                if now < expire_time:
                    return value
        
        # 缓存未命中或已过期，从数据库读取
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT value FROM SystemSettings WHERE key = ?", (key,))
            row = cursor.fetchone()
            value = row["value"] if row else default
        
        # 更新缓存
        with CachedSystemSettings._cache_lock:
            CachedSystemSettings._cache[key] = (value, now + CachedSystemSettings._default_ttl)
        
        return value

    @staticmethod
    def set(key: str, value: str) -> None:
        """设置值（同步更新缓存）
        
        Args:
            key: 设置键名
            value: 设置值
        """
        with get_db_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO SystemSettings (key, value) VALUES (?, ?)",
                (key, value)
            )
        
        # 更新缓存
        with CachedSystemSettings._cache_lock:
            CachedSystemSettings._cache[key] = (value, time.time() + CachedSystemSettings._default_ttl)

    @staticmethod
    def invalidate_cache(key: str | None = None) -> None:
        """清除缓存
        
        Args:
            key: 要清除的键名，如果为 None 则清除所有缓存
        """
        with CachedSystemSettings._cache_lock:
            if key is None:
                CachedSystemSettings._cache.clear()
                logger.info("系统设置缓存已全部清除")
            elif key in CachedSystemSettings._cache:
                del CachedSystemSettings._cache[key]
                logger.debug(f"系统设置缓存键 {key!r} 已清除")

    @staticmethod
    def get_cache_stats() -> dict:
        """获取缓存统计信息
        
        Returns:
            缓存统计字典，包含缓存条目数和命中率估计
        """
        with CachedSystemSettings._cache_lock:
            return {
                "cache_size": len(CachedSystemSettings._cache),
                "ttl_seconds": CachedSystemSettings._default_ttl,
                "keys": list(CachedSystemSettings._cache.keys())
            }

    @staticmethod
    def set_ttl(seconds: int) -> None:
        """设置缓存过期时间
        
        Args:
            seconds: 缓存过期时间（秒）
        """
        CachedSystemSettings._default_ttl = max(1, seconds)
        logger.info(f"系统设置缓存 TTL 已设置为 {seconds} 秒")