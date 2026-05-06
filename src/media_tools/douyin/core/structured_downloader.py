"""基于接口的下载器实现 - 使用组合模式分离职责"""
from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from media_tools.logger import get_logger
from media_tools.core.exceptions import DownloadError

from .interface import (
    VideoInfo,
    VideoFetcher,
    VideoStorage,
    VideoMetadataStore,
    Downloader,
)

logger = get_logger('structured_downloader')


MIN_VIDEO_BYTES = 10240  # 10KB


class F2VideoFetcher(VideoFetcher):
    """基于 F2 SDK 的视频获取器实现"""
    
    def __init__(self):
        self._f2_kwargs = None
    
    def _get_f2_kwargs(self) -> dict:
        if self._f2_kwargs is None:
            from .f2_helper import get_f2_kwargs
            self._f2_kwargs = get_f2_kwargs()
        return self._f2_kwargs
    
    async def fetch_video_list(
        self,
        uid: str,
        max_counts: int = 50,
        interval: Optional[str] = None,
    ) -> List[VideoInfo]:
        """获取用户视频列表"""
        from .f2_helper import get_user_videos
        
        kwargs = self._get_f2_kwargs()
        video_list = await get_user_videos(uid, max_counts, interval, **kwargs)
        
        result = []
        for video in video_list:
            aweme_id = str(video.get("aweme_id", ""))
            title = video.get("desc", "")
            url = video.get("share_url", "")
            author = video.get("author", {}).get("nickname", "")
            author_id = str(video.get("author", {}).get("uid", ""))
            
            if aweme_id:
                result.append(VideoInfo(
                    aweme_id=aweme_id,
                    title=title,
                    url=url,
                    author=author,
                    author_id=author_id,
                    metadata=video,
                ))
        
        return result
    
    async def fetch_video_by_url(self, url: str) -> VideoInfo:
        """根据 URL 获取视频信息"""
        from .f2_helper import get_video_info_by_url
        
        kwargs = self._get_f2_kwargs()
        video = await get_video_info_by_url(url, **kwargs)
        
        if not video:
            raise DownloadError(f"无法获取视频信息: {url}")
        
        aweme_id = str(video.get("aweme_id", ""))
        title = video.get("desc", "")
        author = video.get("author", {}).get("nickname", "")
        author_id = str(video.get("author", {}).get("uid", ""))
        
        return VideoInfo(
            aweme_id=aweme_id,
            title=title,
            url=url,
            author=author,
            author_id=author_id,
            metadata=video,
        )
    
    async def download_video(self, video_info: VideoInfo, save_path: Path) -> bool:
        """下载视频文件到指定路径"""
        from .f2_helper import download_video
        
        kwargs = self._get_f2_kwargs()
        try:
            await download_video(video_info.url, save_path, **kwargs)
            return True
        except Exception as e:
            logger.error(f"下载视频失败 {video_info.aweme_id}: {e}")
            return False


class LocalVideoStorage(VideoStorage):
    """本地文件系统视频存储实现"""
    
    def __init__(self, base_path: Optional[Path] = None):
        if base_path is None:
            from media_tools.core.config import get_app_config
            config = get_app_config()
            base_path = config.download_path
        self._base_path = base_path
    
    def get_download_path(self, author_id: str, author_name: str) -> Path:
        """获取作者视频下载目录"""
        from .file_ops import _clean_video_title
        
        safe_name = _clean_video_title(author_name) or author_id
        author_path = self._base_path / safe_name
        author_path.mkdir(parents=True, exist_ok=True)
        return author_path
    
    def save_video(self, video_info: VideoInfo, content: bytes) -> Path:
        """保存视频文件"""
        author_path = self.get_download_path(video_info.author_id, video_info.author)
        safe_title = self._clean_title(video_info.title)
        filename = f"{safe_title}_{video_info.aweme_id}.mp4"
        file_path = author_path / filename
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        return file_path
    
    def exists(self, aweme_id: str, author_id: str) -> bool:
        """检查视频是否已存在"""
        from .downloader import _scan_local_aweme_files
        
        # 使用原有的扫描逻辑保持兼容性
        author_path = self._base_path / author_id
        if not author_path.exists():
            return False
        
        existing, _, _ = _scan_local_aweme_files(author_path)
        return aweme_id in existing
    
    def list_existing(self, author_id: str) -> List[str]:
        """列出已存在的视频 ID"""
        from .downloader import _scan_local_aweme_files
        
        author_path = self._base_path / author_id
        if not author_path.exists():
            return []
        
        existing, _, _ = _scan_local_aweme_files(author_path)
        return list(existing)
    
    def validate_file(self, file_path: Path) -> bool:
        """验证视频文件完整性"""
        try:
            if not file_path.exists() or not file_path.is_file():
                return False
            if file_path.stat().st_size < MIN_VIDEO_BYTES:
                return False
            with file_path.open("rb") as f:
                header = f.read(16)
            return len(header) >= 12 and header[4:8] == b"ftyp"
        except OSError:
            return False
    
    @staticmethod
    def _clean_title(title: str) -> str:
        """清理标题中的非法字符"""
        return re.sub(r'[\\/*?:"<>|]', '_', title)[:50]


class DatabaseMetadataStore(VideoMetadataStore):
    """基于数据库的元数据存储实现"""
    
    def save_metadata(self, video_info: VideoInfo, file_path: Path) -> None:
        """保存视频元数据"""
        from .downloader import _save_single_video_metadata
        
        # 使用原有的元数据保存逻辑
        video_dict = video_info.metadata.copy()
        video_dict.update({
            "aweme_id": video_info.aweme_id,
            "desc": video_info.title,
            "author": {"nickname": video_info.author, "uid": video_info.author_id},
        })
        _save_single_video_metadata(video_dict, video_info.author)
    
    def get_metadata(self, aweme_id: str) -> Optional[Dict[str, Any]]:
        """获取视频元数据"""
        from media_tools.db.core import get_db_connection
        
        try:
            with get_db_connection() as conn:
                row = conn.execute(
                    "SELECT metadata FROM VideoMetadata WHERE aweme_id = ?",
                    (aweme_id,)
                ).fetchone()
                if row:
                    import json
                    return json.loads(row[0])
        except Exception as e:
            logger.error(f"获取元数据失败 {aweme_id}: {e}")
        
        return None
    
    def update_download_time(self, author_id: str) -> None:
        """更新下载时间"""
        from .downloader import _update_last_fetch_time
        _update_last_fetch_time(author_id)


class StructuredDownloader(Downloader):
    """结构化下载器 - 使用组合模式协调各组件"""
    
    def __init__(
        self,
        fetcher: Optional[VideoFetcher] = None,
        storage: Optional[VideoStorage] = None,
        metadata_store: Optional[VideoMetadataStore] = None,
    ):
        self._fetcher = fetcher or F2VideoFetcher()
        self._storage = storage or LocalVideoStorage()
        self._metadata_store = metadata_store or DatabaseMetadataStore()
        self._progress: Dict[str, Dict[str, Any]] = {}
    
    async def download_by_url(
        self,
        url: str,
        skip_existing: bool = True,
        task_id: Optional[str] = None,
    ) -> Tuple[int, int]:
        """根据 URL 下载视频"""
        try:
            video_info = await self._fetcher.fetch_video_by_url(url)
            
            if skip_existing and self._storage.exists(video_info.aweme_id, video_info.author_id):
                logger.info(f"视频已存在，跳过: {video_info.aweme_id}")
                return (0, 1)
            
            author_path = self._storage.get_download_path(video_info.author_id, video_info.author)
            filename = f"{self._storage._clean_title(video_info.title)}_{video_info.aweme_id}.mp4"
            save_path = author_path / filename
            
            success = await self._fetcher.download_video(video_info, save_path)
            
            if success:
                self._metadata_store.save_metadata(video_info, save_path)
                self._metadata_store.update_download_time(video_info.author_id)
                return (1, 0)
            else:
                return (0, 1)
        
        except Exception as e:
            logger.error(f"下载失败 {url}: {e}")
            raise DownloadError(str(e), url=url) from e
    
    async def download_by_uid(
        self,
        uid: str,
        max_counts: int = 50,
        skip_existing: bool = True,
        task_id: Optional[str] = None,
        interval: Optional[str] = None,
    ) -> Tuple[int, int]:
        """根据用户 ID 下载视频"""
        try:
            video_list = await self._fetcher.fetch_video_list(uid, max_counts, interval)
            
            downloaded = 0
            skipped = 0
            
            for video_info in video_list:
                if skip_existing and self._storage.exists(video_info.aweme_id, video_info.author_id):
                    skipped += 1
                    continue
                
                author_path = self._storage.get_download_path(video_info.author_id, video_info.author)
                filename = f"{self._storage._clean_title(video_info.title)}_{video_info.aweme_id}.mp4"
                save_path = author_path / filename
                
                success = await self._fetcher.download_video(video_info, save_path)
                
                if success:
                    self._metadata_store.save_metadata(video_info, save_path)
                    downloaded += 1
                else:
                    skipped += 1
            
            if downloaded > 0:
                self._metadata_store.update_download_time(uid)
            
            return (downloaded, skipped)
        
        except Exception as e:
            logger.error(f"批量下载失败 uid={uid}: {e}")
            raise DownloadError(str(e)) from e
    
    def get_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取下载进度"""
        return self._progress.get(task_id)


# 全局实例
_default_downloader: Optional[StructuredDownloader] = None


def get_structured_downloader() -> StructuredDownloader:
    """获取结构化下载器实例"""
    global _default_downloader
    if _default_downloader is None:
        _default_downloader = StructuredDownloader()
    return _default_downloader