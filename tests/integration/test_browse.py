"""
浏览功能集成测试

测试排行榜、分类浏览、本子详情等功能。
"""

import pytest

pytestmark = [pytest.mark.integration]


class TestRankingIntegration:
    """排行榜功能集成测试"""

    @pytest.mark.asyncio
    async def test_week_ranking(self, browser):
        """测试周排行榜"""
        results = await browser.get_week_ranking(page=1)

        assert isinstance(results, list)
        assert len(results) > 0, "周排行榜应该有数据"

    @pytest.mark.asyncio
    async def test_month_ranking(self, browser):
        """测试月排行榜"""
        results = await browser.get_month_ranking(page=1)

        assert isinstance(results, list)
        assert len(results) > 0, "月排行榜应该有数据"

    @pytest.mark.asyncio
    async def test_day_ranking(self, browser):
        """测试日排行榜"""
        results = await browser.get_day_ranking(page=1)

        assert isinstance(results, list)
        # 日排行榜可能在某些时段为空


class TestCategoryIntegration:
    """分类浏览集成测试"""

    @pytest.mark.asyncio
    async def test_category_all_hot(self, browser):
        """测试全分类热门"""
        results = await browser.get_category_albums(
            category="all", order_by="hot", time_range="week", page=1
        )

        assert isinstance(results, list)
        assert len(results) > 0, "全分类热门应该有数据"

    @pytest.mark.asyncio
    async def test_category_hanman(self, browser):
        """测试韩漫分类"""
        results = await browser.get_category_albums(
            category="hanman", order_by="hot", time_range="week", page=1
        )

        assert isinstance(results, list)
        # 韩漫分类应该有内容

    @pytest.mark.asyncio
    async def test_category_doujin(self, browser):
        """测试同人分类"""
        results = await browser.get_category_albums(
            category="doujin", order_by="new", time_range="month", page=1
        )

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_category_different_orders(self, browser):
        """测试不同排序方式"""
        orders = ["hot", "new", "pic", "like"]

        for order in orders:
            results = await browser.get_category_albums(
                category="all", order_by=order, time_range="week", page=1
            )
            assert isinstance(results, list), f"排序 {order} 应该返回列表"


class TestAlbumDetailIntegration:
    """本子详情集成测试"""

    @pytest.mark.asyncio
    async def test_get_album_detail(self, browser, test_album_id):
        """测试获取本子详情"""
        detail = await browser.get_album_detail(test_album_id)

        assert detail is not None, f"应该能获取 ID {test_album_id} 的详情"

        # 验证详情包含必要字段
        if isinstance(detail, dict):
            assert "id" in detail or "title" in detail
        else:
            assert hasattr(detail, "id") or hasattr(detail, "title")

    @pytest.mark.asyncio
    async def test_get_album_detail_invalid_id(self, browser):
        """测试无效 ID"""
        detail = await browser.get_album_detail("999999999")

        # 无效 ID 应该返回 None 或抛出异常
        # 这里只验证不会崩溃

    @pytest.mark.asyncio
    async def test_get_photo_id_by_index(self, browser, test_album_id):
        """测试获取章节 ID"""
        result = await browser.get_photo_id_by_index(test_album_id, 1)

        # 结果可能是 tuple (photo_id, title, total) 或 None
        if result is not None:
            assert len(result) >= 2, "应该返回包含 photo_id 和 title 的元组"


class TestAlbumCoverIntegration:
    """封面下载集成测试"""

    @pytest.mark.asyncio
    async def test_get_album_cover(self, browser, test_album_id, temp_download_dir):
        """测试下载封面"""
        cover_path = await browser.get_album_cover(test_album_id, temp_download_dir)

        if cover_path is not None:
            assert cover_path.exists(), "封面文件应该存在"
            assert cover_path.stat().st_size > 0, "封面文件不应为空"
