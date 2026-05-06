"""Tests for the structured downloader components."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from media_tools.douyin.core.interface import (
    VideoInfo,
    VideoFetcher,
    VideoStorage,
    VideoMetadataStore,
)

from media_tools.douyin.core.structured_downloader import (
    F2VideoFetcher,
    LocalVideoStorage,
    DatabaseMetadataStore,
    StructuredDownloader,
    get_structured_downloader,
)


class VideoInfoTests(unittest.TestCase):
    """Tests for VideoInfo data class."""

    def test_video_info_creation(self) -> None:
        """Test VideoInfo creation."""
        video = VideoInfo(
            aweme_id="123456789012345",
            title="Test Video",
            url="https://example.com/video",
            author="Test Author",
            author_id="author123",
            duration=120,
            cover_url="https://example.com/cover.jpg",
        )
        
        self.assertEqual(video.aweme_id, "123456789012345")
        self.assertEqual(video.title, "Test Video")
        self.assertEqual(video.url, "https://example.com/video")
        self.assertEqual(video.author, "Test Author")
        self.assertEqual(video.author_id, "author123")
        self.assertEqual(video.duration, 120)
        self.assertEqual(video.cover_url, "https://example.com/cover.jpg")
        self.assertEqual(video.metadata, {})


class LocalVideoStorageTests(unittest.TestCase):
    """Tests for LocalVideoStorage."""

    def test_clean_title(self) -> None:
        """Test title cleaning."""
        cleaned = LocalVideoStorage._clean_title("Test/Video: Title?")
        self.assertEqual(cleaned, "Test_Video_ Title_")

    def test_clean_title_truncation(self) -> None:
        """Test title truncation."""
        long_title = "A" * 100
        cleaned = LocalVideoStorage._clean_title(long_title)
        self.assertEqual(len(cleaned), 50)


class StructuredDownloaderTests(unittest.TestCase):
    """Tests for StructuredDownloader."""

    def test_downloader_is_singleton(self) -> None:
        """Test get_structured_downloader returns singleton."""
        d1 = get_structured_downloader()
        d2 = get_structured_downloader()
        self.assertIs(d1, d2)

    @patch("media_tools.douyin.core.structured_downloader.F2VideoFetcher")
    @patch("media_tools.douyin.core.structured_downloader.LocalVideoStorage")
    @patch("media_tools.douyin.core.structured_downloader.DatabaseMetadataStore")
    def test_downloader_with_custom_components(
        self,
        mock_metadata: MagicMock,
        mock_storage: MagicMock,
        mock_fetcher: MagicMock,
    ) -> None:
        """Test StructuredDownloader with custom components."""
        downloader = StructuredDownloader(
            fetcher=mock_fetcher,
            storage=mock_storage,
            metadata_store=mock_metadata,
        )
        
        self.assertIs(downloader._fetcher, mock_fetcher)
        self.assertIs(downloader._storage, mock_storage)
        self.assertIs(downloader._metadata_store, mock_metadata)


class InterfaceTests(unittest.TestCase):
    """Tests for interface definitions."""

    def test_video_fetcher_is_abstract(self) -> None:
        """Test VideoFetcher is abstract."""
        with self.assertRaises(TypeError):
            VideoFetcher()  # type: ignore

    def test_video_storage_is_abstract(self) -> None:
        """Test VideoStorage is abstract."""
        with self.assertRaises(TypeError):
            VideoStorage()  # type: ignore

    def test_metadata_store_is_abstract(self) -> None:
        """Test VideoMetadataStore is abstract."""
        with self.assertRaises(TypeError):
            VideoMetadataStore()  # type: ignore


if __name__ == "__main__":
    unittest.main()