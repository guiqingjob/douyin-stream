#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI 核心模块

导出接口：
- VideoInfo, VideoFetcher, VideoStorage, VideoMetadataStore, Downloader
- F2VideoFetcher, LocalVideoStorage, DatabaseMetadataStore, StructuredDownloader
- get_structured_downloader
"""

from .interface import (
    VideoInfo,
    VideoFetcher,
    VideoStorage,
    VideoMetadataStore,
    Downloader,
)

from .structured_downloader import (
    F2VideoFetcher,
    LocalVideoStorage,
    DatabaseMetadataStore,
    StructuredDownloader,
    get_structured_downloader,
)

__all__ = [
    # 接口定义
    "VideoInfo",
    "VideoFetcher",
    "VideoStorage",
    "VideoMetadataStore",
    "Downloader",
    # 实现类
    "F2VideoFetcher",
    "LocalVideoStorage",
    "DatabaseMetadataStore",
    "StructuredDownloader",
    # 工厂函数
    "get_structured_downloader",
]
