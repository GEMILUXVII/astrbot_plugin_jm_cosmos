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


class TestBrowserErrorPropagation:
    """搜索/详情的网络错误应向上传播，而非被吞成空结果/未找到"""

    @pytest.mark.asyncio
    async def test_get_album_detail_propagates_errors(
        self, config_manager, monkeypatch
    ):
        from core.browser import JMBrowser

        browser = JMBrowser(config_manager)
        client = MagicMock()
        client.get_album_detail.side_effect = RuntimeError("network down")

        fake_option = MagicMock()
        fake_option.new_jm_client.return_value = client

        monkeypatch.setattr(browser, "_get_option", lambda: fake_option)
        monkeypatch.setattr(JMBrowser, "is_available", staticmethod(lambda: True))

        with pytest.raises(RuntimeError, match="network down"):
            await browser.get_album_detail("123456")

    @pytest.mark.asyncio
    async def test_search_albums_propagates_errors(self, config_manager, monkeypatch):
        from core.browser import JMBrowser

        browser = JMBrowser(config_manager)
        client = MagicMock()
        client.search_site.side_effect = RuntimeError("boom")

        fake_option = MagicMock()
        fake_option.new_jm_client.return_value = client

        monkeypatch.setattr(browser, "_get_option", lambda: fake_option)
        monkeypatch.setattr(JMBrowser, "is_available", staticmethod(lambda: True))

        with pytest.raises(RuntimeError, match="boom"):
            await browser.search_albums("keyword")

    @pytest.mark.asyncio
    async def test_get_photo_id_propagates_errors(self, config_manager, monkeypatch):
        from core.browser import JMBrowser

        browser = JMBrowser(config_manager)
        client = MagicMock()
        client.get_album_detail.side_effect = RuntimeError("net")

        fake_option = MagicMock()
        fake_option.new_jm_client.return_value = client

        monkeypatch.setattr(browser, "_get_option", lambda: fake_option)
        monkeypatch.setattr(JMBrowser, "is_available", staticmethod(lambda: True))

        with pytest.raises(RuntimeError, match="net"):
            await browser.get_photo_id_by_index("123456", 1)

    @pytest.mark.asyncio
    async def test_get_photo_id_out_of_range_returns_none(
        self, config_manager, monkeypatch
    ):
        from core.browser import JMBrowser

        browser = JMBrowser(config_manager)
        album = MagicMock()
        album.episode_list = [("p1", 1, "第1话"), ("p2", 2, "第2话")]
        client = MagicMock()
        client.get_album_detail.return_value = album

        fake_option = MagicMock()
        fake_option.new_jm_client.return_value = client

        monkeypatch.setattr(browser, "_get_option", lambda: fake_option)
        monkeypatch.setattr(JMBrowser, "is_available", staticmethod(lambda: True))

        # 章节越界：返回 None（而非抛异常），表示“章节不存在”
        assert await browser.get_photo_id_by_index("123456", 99) is None

    @pytest.mark.asyncio
    async def test_ranking_propagates_errors(self, config_manager, monkeypatch):
        from core.browser import JMBrowser

        browser = JMBrowser(config_manager)
        client = MagicMock()
        client.week_ranking.side_effect = RuntimeError("rank boom")

        fake_option = MagicMock()
        fake_option.new_jm_client.return_value = client

        monkeypatch.setattr(browser, "_get_option", lambda: fake_option)
        monkeypatch.setattr(JMBrowser, "is_available", staticmethod(lambda: True))

        with pytest.raises(RuntimeError, match="rank boom"):
            await browser.get_week_ranking(1)

    @pytest.mark.asyncio
    async def test_get_favorites_propagates_errors(self, config_manager, monkeypatch):
        from core.browser import JMBrowser

        browser = JMBrowser(config_manager)
        client = MagicMock()
        client.favorite_folder.side_effect = RuntimeError("fav boom")

        monkeypatch.setattr(JMBrowser, "is_available", staticmethod(lambda: True))

        with pytest.raises(RuntimeError, match="fav boom"):
            await browser.get_favorites(client, page=1)
