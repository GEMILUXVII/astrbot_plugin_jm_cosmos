"""
浏览查询器测试

测试 core/browser.py 中的 JMBrowser 类。
使用 mock 避免实际网络请求。
"""

from unittest.mock import MagicMock, patch

import pytest


class TestJMBrowserInit:
    """JMBrowser 初始化测试"""

    def test_init_with_config_manager(self, config_manager):
        """测试使用配置管理器初始化"""
        from core.browser import JMBrowser

        browser = JMBrowser(config_manager)
        assert browser.config is config_manager


class TestJMBrowserAvailability:
    """JMBrowser 可用性测试"""

    def test_is_available_returns_bool(self, config_manager):
        """测试 is_available 返回布尔值"""
        from core.browser import JMBrowser

        browser = JMBrowser(config_manager)
        result = browser.is_available()
        assert isinstance(result, bool)


class TestJMBrowserSearchAlbums:
    """JMBrowser search_albums 测试"""

    @pytest.mark.asyncio
    async def test_search_albums_jmcomic_unavailable(self, config_manager):
        """测试 jmcomic 不可用时返回空列表"""
        from core.browser import JMBrowser

        browser = JMBrowser(config_manager)

        with patch.object(browser, "is_available", return_value=False):
            result = await browser.search_albums("测试关键词")

        assert result == []

    @pytest.mark.asyncio
    async def test_search_albums_option_unavailable(self, config_manager):
        """测试无法创建配置时返回空列表"""
        from core.browser import JMBrowser

        browser = JMBrowser(config_manager)

        with patch.object(browser, "is_available", return_value=True):
            with patch.object(browser, "_get_option", return_value=None):
                result = await browser.search_albums("测试关键词")

        assert result == []


class TestJMBrowserGetAlbumDetail:
    """JMBrowser get_album_detail 测试"""

    @pytest.mark.asyncio
    async def test_get_album_detail_jmcomic_unavailable(self, config_manager):
        """测试 jmcomic 不可用时返回 None"""
        from core.browser import JMBrowser

        browser = JMBrowser(config_manager)

        with patch.object(browser, "is_available", return_value=False):
            result = await browser.get_album_detail("123456")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_album_detail_option_unavailable(self, config_manager):
        """测试无法创建配置时返回 None"""
        from core.browser import JMBrowser

        browser = JMBrowser(config_manager)

        with patch.object(browser, "is_available", return_value=True):
            with patch.object(browser, "_get_option", return_value=None):
                result = await browser.get_album_detail("123456")

        assert result is None


class TestJMBrowserGetPhotoIdByIndex:
    """JMBrowser get_photo_id_by_index 测试"""

    @pytest.mark.asyncio
    async def test_get_photo_id_jmcomic_unavailable(self, config_manager):
        """测试 jmcomic 不可用时返回 None"""
        from core.browser import JMBrowser

        browser = JMBrowser(config_manager)

        with patch.object(browser, "is_available", return_value=False):
            result = await browser.get_photo_id_by_index("123456", 1)

        assert result is None


class TestJMBrowserRankings:
    """JMBrowser 排行榜测试"""

    @pytest.mark.asyncio
    async def test_get_week_ranking_jmcomic_unavailable(self, config_manager):
        """测试周排行榜 jmcomic 不可用时返回空列表"""
        from core.browser import JMBrowser

        browser = JMBrowser(config_manager)

        with patch.object(browser, "is_available", return_value=False):
            result = await browser.get_week_ranking()

        assert result == []

    @pytest.mark.asyncio
    async def test_get_month_ranking_jmcomic_unavailable(self, config_manager):
        """测试月排行榜 jmcomic 不可用时返回空列表"""
        from core.browser import JMBrowser

        browser = JMBrowser(config_manager)

        with patch.object(browser, "is_available", return_value=False):
            result = await browser.get_month_ranking()

        assert result == []

    @pytest.mark.asyncio
    async def test_get_day_ranking_jmcomic_unavailable(self, config_manager):
        """测试日排行榜 jmcomic 不可用时返回空列表"""
        from core.browser import JMBrowser

        browser = JMBrowser(config_manager)

        with patch.object(browser, "is_available", return_value=False):
            result = await browser.get_day_ranking()

        assert result == []


class TestJMBrowserCategoryAlbums:
    """JMBrowser get_category_albums 测试"""

    @pytest.mark.asyncio
    async def test_get_category_albums_jmcomic_unavailable(self, config_manager):
        """测试分类浏览 jmcomic 不可用时返回空列表"""
        from core.browser import JMBrowser

        browser = JMBrowser(config_manager)

        with patch.object(browser, "is_available", return_value=False):
            result = await browser.get_category_albums(
                category="hanman", order_by="hot", time_range="week", page=1
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_get_category_albums_default_params(self, config_manager):
        """测试分类浏览默认参数"""
        from core.browser import JMBrowser

        browser = JMBrowser(config_manager)

        # 即使 jmcomic 不可用，也应该能正常调用并返回空列表
        with patch.object(browser, "is_available", return_value=False):
            result = await browser.get_category_albums()

        assert isinstance(result, list)


class TestJMBrowserGetAlbumCover:
    """JMBrowser get_album_cover 测试"""

    @pytest.mark.asyncio
    async def test_get_album_cover_jmcomic_unavailable(self, config_manager, temp_dir):
        """测试封面下载 jmcomic 不可用时返回 None"""
        from core.browser import JMBrowser

        browser = JMBrowser(config_manager)

        with patch.object(browser, "is_available", return_value=False):
            result = await browser.get_album_cover("123456", temp_dir)

        assert result is None


class TestJMBrowserGetFavorites:
    """JMBrowser get_favorites 测试"""

    @pytest.mark.asyncio
    async def test_get_favorites_returns_tuple(self, config_manager):
        """测试收藏夹返回元组格式"""
        from core.browser import JMBrowser

        browser = JMBrowser(config_manager)

        # Mock client
        mock_client = MagicMock()

        with patch.object(browser, "is_available", return_value=False):
            result = await browser.get_favorites(mock_client, page=1)

        # 应返回空的收藏列表和收藏夹列表
        assert isinstance(result, tuple)
        assert len(result) == 2
