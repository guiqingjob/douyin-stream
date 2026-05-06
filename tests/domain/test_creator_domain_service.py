"""领域服务单元测试 - CreatorDomainService"""
import pytest
from unittest.mock import Mock
from datetime import datetime

from media_tools.domain.entities import Creator
from media_tools.domain.services import CreatorDomainService


class TestCreatorDomainService:
    """创作者领域服务测试"""

    def setup_method(self):
        """设置测试环境"""
        self.mock_creator_repo = Mock()
        self.mock_asset_repo = Mock()
        self.service = CreatorDomainService(self.mock_creator_repo, self.mock_asset_repo)

    def test_create_creator(self):
        """测试创建创作者"""
        creator = self.service.create_creator("creator1", "sec1", "测试创作者", "douyin")
        
        assert creator.uid == "creator1"
        assert creator.nickname == "测试创作者"
        assert creator.platform.value == "douyin"
        
        self.mock_creator_repo.save.assert_called_once()

    def test_create_creator_without_avatar(self):
        """测试创建创作者（不带头像）"""
        creator = self.service.create_creator("creator1", "sec1", "测试创作者")
        
        assert creator.avatar is None
        self.mock_creator_repo.save.assert_called_once()

    def test_get_creator(self):
        """测试获取创作者"""
        mock_creator = Creator(uid="creator1", sec_user_id="sec1", nickname="测试创作者")
        self.mock_creator_repo.find_by_id.return_value = mock_creator
        
        result = self.service.get_creator("creator1")
        
        assert result == mock_creator
        self.mock_creator_repo.find_by_id.assert_called_once_with("creator1")

    def test_get_creator_not_found(self):
        """测试获取不存在的创作者"""
        self.mock_creator_repo.find_by_id.return_value = None
        
        result = self.service.get_creator("creator1")
        
        assert result is None

    def test_list_creators(self):
        """测试列出所有创作者"""
        mock_creators = [
            Creator(uid="creator1", sec_user_id="sec1", nickname="创作者1"),
            Creator(uid="creator2", sec_user_id="sec2", nickname="创作者2"),
        ]
        self.mock_creator_repo.find_all.return_value = mock_creators
        
        result = self.service.list_creators()
        
        assert len(result) == 2
        self.mock_creator_repo.find_all.assert_called_once()

    def test_update_creator_info(self):
        """测试更新创作者信息"""
        mock_creator = Creator(uid="creator1", sec_user_id="sec1", nickname="旧昵称")
        self.mock_creator_repo.find_by_id.return_value = mock_creator
        
        self.service.update_creator_info("creator1", nickname="新昵称", avatar="http://new.jpg")
        
        assert mock_creator.nickname == "新昵称"
        assert mock_creator.avatar == "http://new.jpg"
        self.mock_creator_repo.save.assert_called_once()

    def test_update_creator_info_not_found(self):
        """测试更新不存在的创作者"""
        self.mock_creator_repo.find_by_id.return_value = None
        
        self.service.update_creator_info("creator1", nickname="新昵称")
        
        self.mock_creator_repo.save.assert_not_called()

    def test_update_creator_info_partial(self):
        """测试部分更新创作者信息"""
        mock_creator = Creator(uid="creator1", sec_user_id="sec1", nickname="旧昵称", avatar="http://old.jpg")
        self.mock_creator_repo.find_by_id.return_value = mock_creator
        
        self.service.update_creator_info("creator1", nickname="新昵称")
        
        assert mock_creator.nickname == "新昵称"
        assert mock_creator.avatar == "http://old.jpg"  # 保持不变

    def test_delete_creator(self):
        """测试删除创作者"""
        self.service.delete_creator("creator1")
        
        self.mock_creator_repo.delete.assert_called_once_with("creator1")

    def test_update_last_fetch_time(self):
        """测试更新获取时间"""
        mock_creator = Creator(uid="creator1", sec_user_id="sec1", nickname="测试创作者")
        self.mock_creator_repo.find_by_id.return_value = mock_creator
        
        self.service.update_last_fetch_time("creator1")
        
        assert mock_creator.last_fetch_time is not None
        self.mock_creator_repo.save.assert_called_once()