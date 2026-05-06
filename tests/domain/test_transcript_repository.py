"""TranscriptRepository 测试"""
from __future__ import annotations

import tempfile
import pytest
from pathlib import Path
from typing import Optional

from media_tools.domain.entities.transcript import Transcript
from media_tools.domain.repositories.transcript_repository import TranscriptRepository
from media_tools.infrastructure.db.transcript_repository import (
    SQLiteTranscriptRepository,
    create_transcript_repository,
)


class TestSQLiteTranscriptRepository:
    """SQLiteTranscriptRepository 单元测试"""

    @pytest.fixture
    def repo(self) -> TranscriptRepository:
        """创建测试用仓储实例"""
        return create_transcript_repository()

    @pytest.fixture
    def sample_transcript(self) -> Transcript:
        """创建示例转写数据"""
        return Transcript(
            transcript_id="test_transcript_001",
            asset_id="test_asset_001",
            text="这是测试转写文本内容",
            path=Path("/tmp/test_transcript.json"),
            preview="这是测试转写预览...",
        )

    def test_create_transcript_repository(self):
        """测试创建 TranscriptRepository 实例"""
        repo = create_transcript_repository()
        assert repo is not None
        assert isinstance(repo, SQLiteTranscriptRepository)

    def test_save_transcript(self, repo: TranscriptRepository, sample_transcript: Transcript):
        """测试保存转写"""
        repo.save(sample_transcript)

    def test_find_by_id_returns_transcript(self, repo: TranscriptRepository, sample_transcript: Transcript):
        """测试通过 ID 查询转写"""
        repo.save(sample_transcript)
        result = repo.find_by_id("test_asset_001")
        assert result is not None
        assert isinstance(result, Transcript)
        assert result.asset_id == "test_asset_001"

    def test_find_by_id_returns_none_for_nonexistent(self, repo: TranscriptRepository):
        """测试查询不存在的转写返回 None"""
        result = repo.find_by_id("nonexistent_id")
        assert result is None

    def test_find_by_asset_returns_transcript(self, repo: TranscriptRepository, sample_transcript: Transcript):
        """测试通过素材 ID 查询转写"""
        repo.save(sample_transcript)
        result = repo.find_by_asset("test_asset_001")
        assert result is not None
        assert isinstance(result, Transcript)
        assert result.asset_id == "test_asset_001"

    def test_find_by_asset_returns_none_for_nonexistent(self, repo: TranscriptRepository):
        """测试查询不存在的素材转写返回 None"""
        result = repo.find_by_asset("nonexistent_asset")
        assert result is None

    def test_exists_returns_true_for_existing(self, repo: TranscriptRepository, sample_transcript: Transcript):
        """测试检查已存在的转写返回 True"""
        repo.save(sample_transcript)
        assert repo.exists("test_asset_001") is True

    def test_exists_returns_false_for_nonexistent(self, repo: TranscriptRepository):
        """测试检查不存在的转写返回 False"""
        assert repo.exists("nonexistent_asset") is False

    def test_update_preview(self, repo: TranscriptRepository, sample_transcript: Transcript):
        """测试更新转写预览"""
        repo.save(sample_transcript)
        new_preview = "新的预览内容"
        repo.update_preview("test_asset_001", new_preview)
        result = repo.find_by_id("test_asset_001")
        assert result is not None
        assert result.preview == new_preview

    def test_delete_transcript(self, repo: TranscriptRepository, sample_transcript: Transcript):
        """测试删除转写"""
        repo.save(sample_transcript)
        assert repo.exists("test_asset_001") is True
        repo.delete("test_asset_001")
        assert repo.exists("test_asset_001") is False

    def test_find_all_returns_list(self, repo: TranscriptRepository):
        """测试查询所有转写返回列表"""
        result = repo.find_all()
        assert isinstance(result, list)

    def test_save_with_none_path(self, repo: TranscriptRepository):
        """测试保存路径为 None 的转写"""
        transcript = Transcript(
            transcript_id="test_none_path",
            asset_id="test_asset_none_path",
            text="无路径的转写",
            path=None,
            preview="预览",
        )
        repo.save(transcript)
        result = repo.find_by_id("test_asset_none_path")
        assert result is not None
        assert result.path is None

    def test_save_with_empty_text(self, repo: TranscriptRepository):
        """测试保存空文本的转写"""
        transcript = Transcript(
            transcript_id="test_empty_text",
            asset_id="test_asset_empty_text",
            text="",
            path=Path("/tmp/empty.json"),
            preview="预览",
        )
        repo.save(transcript)
        result = repo.find_by_id("test_asset_empty_text")
        assert result is not None
        assert result.text == ""
