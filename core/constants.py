"""
JM-Cosmos II 常量定义模块

集中管理分类、排序、时间等常量映射。
"""

# ==================== API 参数映射 ====================
# 这些映射用于将用户输入转换为 jmcomic 库接受的 API 参数

# 分类映射：用户输入 -> API 参数
CATEGORY_MAP = {
    "all": "0",
    "doujin": "doujin",
    "single": "single",
    "short": "short",
    "hanman": "hanman",
    "meiman": "meiman",
    "3d": "3D",
    "cosplay": "doujin_cosplay",
    "another": "another",
}

# 排序映射：用户输入 -> API 参数
ORDER_MAP = {
    "new": "mr",  # 最新
    "hot": "mv",  # 最热（观看数）
    "pic": "mp",  # 图片多
    "like": "tf",  # 点赞多
}

# 时间映射：用户输入 -> API 参数
TIME_MAP = {
    "day": "t",  # 今日
    "week": "w",  # 本周
    "month": "m",  # 本月
    "all": "a",  # 全部时间
}


# ==================== 显示名称映射 ====================
# 这些映射用于在消息中显示友好的中文名称

# 分类显示名称（支持用户输入和 API 参数两种 key）
CATEGORY_NAMES = {
    "all": "全部",
    "0": "全部",
    "doujin": "同人",
    "single": "单本",
    "short": "短篇",
    "hanman": "韩漫",
    "meiman": "美漫",
    "3d": "3D",
    "3D": "3D",
    "cosplay": "Cosplay",
    "doujin_cosplay": "Cosplay",
    "another": "其他",
}

# 排序显示名称（支持用户输入和 API 参数两种 key）
ORDER_NAMES = {
    "new": "最新",
    "mr": "最新",
    "hot": "热门",
    "mv": "热门",
    "pic": "图多",
    "mp": "图多",
    "like": "点赞",
    "tf": "点赞",
}

# 时间显示名称（支持用户输入和 API 参数两种 key）
TIME_NAMES = {
    "day": "今日",
    "t": "今日",
    "week": "本周",
    "w": "本周",
    "month": "本月",
    "m": "本月",
    "all": "全部时间",
    "a": "全部时间",
}


# ==================== 辅助函数 ====================


def get_category_list() -> list[str]:
    """获取所有支持的分类"""
    return list(CATEGORY_MAP.keys())


def get_order_list() -> list[str]:
    """获取所有支持的排序方式"""
    return list(ORDER_MAP.keys())


def get_time_list() -> list[str]:
    """获取所有支持的时间范围"""
    return list(TIME_MAP.keys())
