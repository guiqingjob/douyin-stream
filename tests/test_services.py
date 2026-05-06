"""Tests for service layer."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from media_tools.services.asset_service import AssetService, get_asset_service
from media_tools.services.creator_service import CreatorService, get_creator_service


class AssetServiceTests(unittest.TestCase):
    """Tests for AssetService."""

    def test_service_is_singleton(self) -> None:
        """Test get_asset_service returns singleton."""
        s1 = get_asset_service()
        s2 = get_asset_service()
        self.assertIs(s1, s2)

    @patch("media_tools.services.asset_service.get_db_connection")
    def test_list_assets(self, mock_conn: MagicMock) -> None:
        """Test list_assets."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.return_value.__enter__.return_value.execute.return_value = mock_cursor
        
        result = AssetService.list_assets()
        self.assertEqual(result, [])

    @patch("media_tools.services.asset_service.get_db_connection")
    def test_get_asset_not_found(self, mock_conn: MagicMock) -> None:
        """Test get_asset when not found."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.return_value.__enter__.return_value.execute.return_value = mock_cursor
        
        result = AssetService.get_asset("nonexistent")
        self.assertIsNone(result)


class CreatorServiceTests(unittest.TestCase):
    """Tests for CreatorService."""

    def test_service_is_singleton(self) -> None:
        """Test get_creator_service returns singleton."""
        s1 = get_creator_service()
        s2 = get_creator_service()
        self.assertIs(s1, s2)

    @patch("media_tools.services.creator_service.get_db_connection")
    def test_list_creators(self, mock_conn: MagicMock) -> None:
        """Test list_creators."""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.return_value.__enter__.return_value.execute.return_value = mock_cursor
        
        result = CreatorService.list_creators()
        self.assertEqual(result, [])

    @patch("media_tools.services.creator_service.get_db_connection")
    def test_get_creator_not_found(self, mock_conn: MagicMock) -> None:
        """Test get_creator when not found."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn.return_value.__enter__.return_value.execute.return_value = mock_cursor
        
        result = CreatorService.get_creator("nonexistent")
        self.assertIsNone(result)

    def test_clean_name(self) -> None:
        """Test _clean_name method."""
        cleaned = CreatorService._clean_name("Test/Creator: Name?")
        self.assertEqual(cleaned, "Test_Creator_ Name_")

    def test_clean_name_truncation(self) -> None:
        """Test _clean_name truncation."""
        long_name = "A" * 100
        cleaned = CreatorService._clean_name(long_name)
        self.assertEqual(len(cleaned), 50)


if __name__ == "__main__":
    unittest.main()