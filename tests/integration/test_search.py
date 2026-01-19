"""
搜索功能集成测试

使用真实 jmcomic 库测试搜索功能。
"""

import pytest

pytestmark = [pytest.mark.integration]


class TestSearchIntegration:
    """搜索功能集成测试"""

    @pytest.mark.asyncio
    async def test_search_returns_results(self, browser):
        """测试搜索返回结果"""
        results = await browser.search_albums("韩漫", page=1)

        assert isinstance(results, list)
        assert len(results) > 0, "搜索应该返回结果"

        # 验证结果结构
        first_result = results[0]
        assert "id" in first_result or hasattr(first_result, "id")

    @pytest.mark.asyncio
    async def test_search_with_tag(self, browser):
        """测试标签搜索"""
        results = await browser.search_albums("NTR", page=1)

        assert isinstance(results, list)
        # 某些标签可能没有结果，只检查返回类型

    @pytest.mark.asyncio
    async def test_search_empty_keyword(self, browser):
        """测试空关键词搜索"""
        results = await browser.search_albums("", page=1)

        # 空关键词可能返回空列表或默认结果
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_pagination(self, browser):
        """测试搜索分页"""
        page1 = await browser.search_albums("漫画", page=1)
        page2 = await browser.search_albums("漫画", page=2)

        assert isinstance(page1, list)
        assert isinstance(page2, list)

        # 如果都有结果，验证不同页的结果不同
        if len(page1) > 0 and len(page2) > 0:
            # 获取 ID（兼容字典和对象）
            def get_id(item):
                return (
                    item.get("id")
                    if isinstance(item, dict)
                    else getattr(item, "id", None)
                )

            page1_ids = {get_id(r) for r in page1}
            page2_ids = {get_id(r) for r in page2}
            # 不同页应该有不同的结果
            assert page1_ids != page2_ids, "不同页的结果应该不同"

    @pytest.mark.asyncio
    async def test_search_special_characters(self, browser):
        """测试特殊字符搜索"""
        results = await browser.search_albums("女×女", page=1)

        assert isinstance(results, list)
