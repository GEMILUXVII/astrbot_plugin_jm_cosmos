"""
常量模块测试

测试 core/constants.py 中的映射和辅助函数。
"""



class TestCategoryMap:
    """分类映射测试"""

    def test_category_map_has_all_entries(self):
        """测试分类映射包含所有必要条目"""
        from core.constants import CATEGORY_MAP

        expected_keys = {"all", "doujin", "single", "short", "hanman", "meiman", "3d", "cosplay", "another"}
        assert set(CATEGORY_MAP.keys()) == expected_keys

    def test_category_map_values(self):
        """测试分类映射值正确"""
        from core.constants import CATEGORY_MAP

        assert CATEGORY_MAP["all"] == "0"
        assert CATEGORY_MAP["3d"] == "3D"
        assert CATEGORY_MAP["cosplay"] == "doujin_cosplay"


class TestOrderMap:
    """排序映射测试"""

    def test_order_map_has_all_entries(self):
        """测试排序映射包含所有必要条目"""
        from core.constants import ORDER_MAP

        expected_keys = {"new", "hot", "pic", "like"}
        assert set(ORDER_MAP.keys()) == expected_keys

    def test_order_map_values(self):
        """测试排序映射值正确"""
        from core.constants import ORDER_MAP

        assert ORDER_MAP["new"] == "mr"
        assert ORDER_MAP["hot"] == "mv"
        assert ORDER_MAP["pic"] == "mp"
        assert ORDER_MAP["like"] == "tf"


class TestTimeMap:
    """时间映射测试"""

    def test_time_map_has_all_entries(self):
        """测试时间映射包含所有必要条目"""
        from core.constants import TIME_MAP

        expected_keys = {"day", "week", "month", "all"}
        assert set(TIME_MAP.keys()) == expected_keys

    def test_time_map_values(self):
        """测试时间映射值正确"""
        from core.constants import TIME_MAP

        assert TIME_MAP["day"] == "t"
        assert TIME_MAP["week"] == "w"
        assert TIME_MAP["month"] == "m"
        assert TIME_MAP["all"] == "a"


class TestDisplayNames:
    """显示名称映射测试"""

    def test_category_names_bidirectional(self):
        """测试分类显示名称支持双向映射"""
        from core.constants import CATEGORY_NAMES

        # 用户输入 key
        assert CATEGORY_NAMES["all"] == "全部"
        assert CATEGORY_NAMES["hanman"] == "韩漫"
        # API 参数 key
        assert CATEGORY_NAMES["0"] == "全部"
        assert CATEGORY_NAMES["3D"] == "3D"

    def test_order_names_bidirectional(self):
        """测试排序显示名称支持双向映射"""
        from core.constants import ORDER_NAMES

        assert ORDER_NAMES["hot"] == "热门"
        assert ORDER_NAMES["mv"] == "热门"

    def test_time_names_bidirectional(self):
        """测试时间显示名称支持双向映射"""
        from core.constants import TIME_NAMES

        assert TIME_NAMES["week"] == "本周"
        assert TIME_NAMES["w"] == "本周"


class TestHelperFunctions:
    """辅助函数测试"""

    def test_get_category_list(self):
        """测试获取分类列表"""
        from core.constants import get_category_list

        categories = get_category_list()
        assert isinstance(categories, list)
        assert "all" in categories
        assert "hanman" in categories
        assert len(categories) == 9

    def test_get_order_list(self):
        """测试获取排序列表"""
        from core.constants import get_order_list

        orders = get_order_list()
        assert isinstance(orders, list)
        assert "hot" in orders
        assert "new" in orders
        assert len(orders) == 4

    def test_get_time_list(self):
        """测试获取时间列表"""
        from core.constants import get_time_list

        times = get_time_list()
        assert isinstance(times, list)
        assert "week" in times
        assert "all" in times
        assert len(times) == 4
