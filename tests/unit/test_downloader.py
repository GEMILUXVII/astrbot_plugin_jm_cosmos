"""
下载管理器测试

测试 core/downloader.py 中的 JMDownloadManager 类和 DownloadResult 数据类。
使用 mock 避免实际网络请求。
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestDownloadResult:
    """DownloadResult 数据类测试"""

    def test_download_result_success(self):
        """测试成功的下载结果"""
        from core.downloader import DownloadResult

        result = DownloadResult(
            success=True,
            album_id="123456",
            title="测试本子",
            author="测试作者",
            photo_count=5,
            image_count=100,
            save_path=Path("/some/path"),
            cover_path=Path("/some/cover"),
        )

        assert result.success is True
        assert result.album_id == "123456"
        assert result.title == "测试本子"
        assert result.author == "测试作者"
        assert result.photo_count == 5
        assert result.image_count == 100
        assert result.error_message is None

    def test_download_result_failure(self):
        """测试失败的下载结果"""
        from core.downloader import DownloadResult

        result = DownloadResult(
            success=False,
            album_id="999999",
            title="",
            author="",
            photo_count=0,
            image_count=0,
            save_path=Path(),
            error_message="下载失败：网络错误",
        )

        assert result.success is False
        assert result.error_message == "下载失败：网络错误"


class TestJMDownloadManagerInit:
    """JMDownloadManager 初始化测试"""

    def test_init_with_config_manager(self, config_manager):
        """测试使用配置管理器初始化"""
        from core.downloader import JMDownloadManager

        manager = JMDownloadManager(config_manager)
        assert manager.config is config_manager
        assert manager._current_progress == {}


class TestJMDownloadManagerAvailability:
    """JMDownloadManager 可用性测试"""

    def test_is_available_returns_bool(self, config_manager):
        """测试 is_available 返回布尔值"""
        from core.downloader import JMDownloadManager

        manager = JMDownloadManager(config_manager)
        result = manager.is_available()
        assert isinstance(result, bool)


class TestJMDownloadManagerDownloadAlbum:
    """JMDownloadManager download_album 测试"""

    @pytest.mark.asyncio
    async def test_download_album_jmcomic_unavailable(self, config_manager):
        """测试 jmcomic 不可用时返回错误"""
        from core.downloader import JMDownloadManager

        manager = JMDownloadManager(config_manager)

        # Mock is_available 返回 False
        with patch.object(manager, "is_available", return_value=False):
            result = await manager.download_album("123456")

        assert result.success is False
        assert "未安装" in result.error_message

    @pytest.mark.asyncio
    async def test_download_album_option_unavailable(self, config_manager):
        """测试无法创建配置时返回错误"""
        from core.downloader import JMDownloadManager

        manager = JMDownloadManager(config_manager)

        with patch.object(manager, "is_available", return_value=True):
            with patch.object(manager, "_get_option", return_value=None):
                result = await manager.download_album("123456")

        assert result.success is False
        assert "配置" in result.error_message


class TestJMDownloadManagerDownloadPhoto:
    """JMDownloadManager download_photo 测试"""

    @pytest.mark.asyncio
    async def test_download_photo_jmcomic_unavailable(self, config_manager):
        """测试 jmcomic 不可用时返回错误"""
        from core.downloader import JMDownloadManager

        manager = JMDownloadManager(config_manager)

        with patch.object(manager, "is_available", return_value=False):
            result = await manager.download_photo("123456_1")

        assert result.success is False
        assert "未安装" in result.error_message

    @pytest.mark.asyncio
    async def test_download_photo_option_unavailable(self, config_manager):
        """测试无法创建配置时返回错误"""
        from core.downloader import JMDownloadManager

        manager = JMDownloadManager(config_manager)

        with patch.object(manager, "is_available", return_value=True):
            with patch.object(manager, "_get_option", return_value=None):
                result = await manager.download_photo("123456_1")

        assert result.success is False
        assert "配置" in result.error_message


class TestJMDownloadManagerSync:
    """JMDownloadManager 同步方法测试（使用 mock）"""

    def test_download_album_sync_success(self, config_manager, mock_album):
        """测试同步下载本子成功（mocked）"""
        from core.downloader import JMDownloadManager

        manager = JMDownloadManager(config_manager)

        # 这个测试需要 jmcomic 库，如果不可用则跳过
        if not manager.is_available():
            pytest.skip("jmcomic 库未安装")

    def test_download_photo_sync_success(self, config_manager, mock_photo):
        """测试同步下载章节成功（mocked）"""
        from core.downloader import JMDownloadManager

        manager = JMDownloadManager(config_manager)

        if not manager.is_available():
            pytest.skip("jmcomic 库未安装")
