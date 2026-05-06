"""领域服务单元测试 - AssetDomainService"""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime
from pathlib import Path

from media_tools.domain.entities import Asset, VideoStatus, TranscriptStatus, Creator
from media_tools.domain.services import AssetDomainService


class TestAssetDomainService:
    """素材领域服务测试"""

    def setup_method(self):
        """设置测试环境"""
        self.mock_asset_repo = Mock()
        self.mock_creator_repo = Mock()
        self.service = AssetDomainService(self.mock_asset_repo, self.mock_creator_repo)

    def test_create_asset(self):
        """测试创建素材"""
        asset = self.service.create_asset("creator1", "测试视频")
        
        assert asset.asset_id is not None
        assert asset.creator_uid == "creator1"
        assert asset.title == "测试视频"
        assert asset.video_status == VideoStatus.PENDING
        
        self.mock_asset_repo.save.assert_called_once()

    def test_get_asset(self):
        """测试获取素材"""
        mock_asset = Asset(asset_id="asset1", creator_uid="creator1", title="测试视频")
        self.mock_asset_repo.find_by_id.return_value = mock_asset
        
        result = self.service.get_asset("asset1")
        
        assert result == mock_asset
        self.mock_asset_repo.find_by_id.assert_called_once_with("asset1")

    def test_get_asset_not_found(self):
        """测试获取不存在的素材"""
        self.mock_asset_repo.find_by_id.return_value = None
        
        result = self.service.get_asset("asset1")
        
        assert result is None

    def test_list_assets_by_creator(self):
        """测试按创作者列出素材"""
        mock_assets = [
            Asset(asset_id="asset1", creator_uid="creator1", title="视频1"),
            Asset(asset_id="asset2", creator_uid="creator1", title="视频2"),
        ]
        self.mock_asset_repo.find_by_creator.return_value = mock_assets
        
        result = self.service.list_assets("creator1")
        
        assert len(result) == 2
        self.mock_asset_repo.find_by_creator.assert_called_once_with("creator1")

    def test_list_all_assets(self):
        """测试列出所有素材"""
        mock_assets = [
            Asset(asset_id="asset1", creator_uid="creator1", title="视频1"),
            Asset(asset_id="asset2", creator_uid="creator2", title="视频2"),
        ]
        self.mock_asset_repo.find_all.return_value = mock_assets
        
        result = self.service.list_assets()
        
        assert len(result) == 2
        self.mock_asset_repo.find_all.assert_called_once()

    def test_delete_asset(self):
        """测试删除素材"""
        mock_asset = Asset(asset_id="asset1", creator_uid="creator1", title="测试视频")
        self.mock_asset_repo.find_by_id.return_value = mock_asset
        
        self.service.delete_asset("asset1")
        
        self.mock_asset_repo.delete.assert_called_once_with("asset1")

    def test_delete_asset_not_found(self):
        """测试删除不存在的素材"""
        self.mock_asset_repo.find_by_id.return_value = None
        
        self.service.delete_asset("asset1")
        
        self.mock_asset_repo.delete.assert_not_called()

    def test_mark_downloaded(self):
        """测试标记素材已下载"""
        mock_asset = Asset(asset_id="asset1", creator_uid="creator1", title="测试视频")
        mock_creator = Creator(uid="creator1", sec_user_id="sec1", nickname="测试创作者")
        self.mock_asset_repo.find_by_id.return_value = mock_asset
        self.mock_creator_repo.find_by_id.return_value = mock_creator
        
        video_path = Path("/downloads/video.mp4")
        self.service.mark_downloaded("asset1", video_path)
        
        assert mock_asset.video_path == video_path
        assert mock_asset.video_status == VideoStatus.DOWNLOADED
        self.mock_asset_repo.save.assert_called_once()
        self.mock_creator_repo.save.assert_called_once()
        assert mock_creator.downloaded_count == 1

    def test_mark_transcribed(self):
        """测试标记素材已转写"""
        mock_asset = Asset(asset_id="asset1", creator_uid="creator1", title="测试视频")
        mock_creator = Creator(uid="creator1", sec_user_id="sec1", nickname="测试创作者")
        self.mock_asset_repo.find_by_id.return_value = mock_asset
        self.mock_creator_repo.find_by_id.return_value = mock_creator
        
        transcript_path = Path("/downloads/transcript.txt")
        transcript_text = "这是完整的转写内容..."
        preview = "这是转写预览..."
        self.service.mark_transcribed("asset1", transcript_path, transcript_text, preview)
        
        assert mock_asset.transcript_path == transcript_path
        assert mock_asset.transcript_preview == preview
        assert mock_asset.transcript_status == TranscriptStatus.COMPLETED
        self.mock_asset_repo.save.assert_called_once()
        self.mock_creator_repo.save.assert_called_once()
        assert mock_creator.transcript_count == 1

    def test_toggle_starred(self):
        """测试切换收藏状态"""
        mock_asset = Asset(asset_id="asset1", creator_uid="creator1", title="测试视频", is_starred=False)
        self.mock_asset_repo.find_by_id.return_value = mock_asset
        
        result = self.service.toggle_starred("asset1")
        
        assert result is True
        assert mock_asset.is_starred is True
        self.mock_asset_repo.save.assert_called_once()

    def test_get_starred_assets(self):
        """测试获取收藏的素材"""
        mock_assets = [
            Asset(asset_id="asset1", creator_uid="creator1", title="视频1", is_starred=True),
            Asset(asset_id="asset2", creator_uid="creator1", title="视频2", is_starred=True),
        ]
        self.mock_asset_repo.find_starred.return_value = mock_assets
        
        result = self.service.get_starred_assets()
        
        assert len(result) == 2
        self.mock_asset_repo.find_starred.assert_called_once()