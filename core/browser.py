"""
JMComic 浏览查询模块

提供搜索、详情查看、排行榜等浏览功能。
"""

from pathlib import Path

from astrbot.api import logger

try:
    from jmcomic import JmcomicText

    JMCOMIC_AVAILABLE = True
except ImportError:
    JMCOMIC_AVAILABLE = False

from .base import JMClientMixin, JMConfigManager


class JMBrowser(JMClientMixin):
    """JMComic 浏览查询器"""

    def __init__(self, config_manager: JMConfigManager):
        """
        初始化浏览查询器

        Args:
            config_manager: 配置管理器实例
        """
        self.config = config_manager

    # ==================== 搜索功能 ====================

    async def search_albums(self, keyword: str, page: int = 1) -> list[dict]:
        """
        搜索本子

        Args:
            keyword: 搜索关键词
            page: 页码

        Returns:
            搜索结果列表
        """
        if not self.is_available():
            return []

        try:
            option = self._get_option()
            if option is None:
                return []

            return await self._run_sync(self._search_albums_sync, keyword, page, option)
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []

    def _search_albums_sync(self, keyword: str, page: int, option) -> list[dict]:
        """同步搜索本子"""
        try:
            client = option.build_jm_client()
            search_page = client.search_site(keyword, page)

            results = []
            for album_id, title, tags in search_page.iter_id_title_tag():
                results.append(
                    {
                        "id": album_id,
                        "title": title,
                        "author": "",
                        "tags": tags,
                        "category": "",
                    }
                )
            return results
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []

    # ==================== 详情功能 ====================

    async def get_album_detail(self, album_id: str) -> dict | None:
        """
        获取本子详情

        Args:
            album_id: 本子ID

        Returns:
            本子详情字典
        """
        if not self.is_available():
            return None

        try:
            option = self._get_option()
            if option is None:
                return None

            return await self._run_sync(self._get_album_detail_sync, album_id, option)
        except Exception as e:
            logger.error(f"获取详情失败: {e}")
            return None

    def _get_album_detail_sync(self, album_id: str, option) -> dict | None:
        """同步获取本子详情"""
        try:
            client = option.build_jm_client()
            parsed_id = JmcomicText.parse_to_jm_id(album_id)
            album = client.get_album_detail(parsed_id)

            return {
                "id": album.id,
                "title": album.title,
                "author": album.author,
                "tags": album.tags if hasattr(album, "tags") else [],
                "photo_count": len(album),
                "pub_date": str(album.pub_date) if hasattr(album, "pub_date") else "",
                "update_date": str(album.update_date)
                if hasattr(album, "update_date")
                else "",
                "description": album.description
                if hasattr(album, "description")
                else "",
                "likes": album.likes if hasattr(album, "likes") else 0,
                "views": album.views if hasattr(album, "views") else 0,
            }
        except Exception as e:
            logger.error(f"获取详情失败: {e}")
            return None

    async def get_photo_id_by_index(
        self, album_id: str, chapter_index: int
    ) -> tuple[str, str, int] | None:
        """
        根据本子ID和章节序号获取章节的photo_id

        Args:
            album_id: 本子ID
            chapter_index: 章节序号（从1开始）

        Returns:
            (photo_id, photo_title, total_chapters) 或 None（失败时）
        """
        if not self.is_available():
            return None

        try:
            option = self._get_option()
            if option is None:
                return None

            return await self._run_sync(
                self._get_photo_id_by_index_sync, album_id, chapter_index, option
            )
        except Exception as e:
            logger.error(f"获取章节ID失败: {e}")
            return None

    def _get_photo_id_by_index_sync(
        self, album_id: str, chapter_index: int, option
    ) -> tuple[str, str, int] | None:
        """同步获取章节ID"""
        try:
            client = option.build_jm_client()
            parsed_id = JmcomicText.parse_to_jm_id(album_id)
            album = client.get_album_detail(parsed_id)

            total_chapters = len(album.episode_list)

            # 验证章节序号有效性（用户输入从1开始，内部索引从0开始）
            if chapter_index < 1 or chapter_index > total_chapters:
                return None

            # 获取章节信息: (photo_id, photo_index, photo_title)
            photo_id, _, photo_title = album.episode_list[chapter_index - 1]

            return (photo_id, photo_title, total_chapters)
        except Exception as e:
            logger.error(f"获取章节ID失败: {e}")
            return None

    async def get_album_cover(self, album_id: str, save_dir: Path) -> Path | None:
        """
        下载本子封面

        Args:
            album_id: 本子ID
            save_dir: 封面保存目录

        Returns:
            封面文件路径，失败返回 None
        """
        if not self.is_available():
            return None

        try:
            option = self._get_option()
            if option is None:
                return None

            # 确保保存目录存在
            save_dir.mkdir(parents=True, exist_ok=True)

            return await self._run_sync(
                self._get_album_cover_sync, album_id, save_dir, option
            )
        except Exception as e:
            logger.error(f"获取封面失败: {e}")
            return None

    def _get_album_cover_sync(
        self, album_id: str, save_dir: Path, option
    ) -> Path | None:
        """同步下载本子封面"""
        try:
            client = option.build_jm_client()
            parsed_id = JmcomicText.parse_to_jm_id(album_id)

            # 封面保存路径
            cover_path = save_dir / f"{parsed_id}.jpg"

            # 下载封面
            client.download_album_cover(parsed_id, str(cover_path))

            if cover_path.exists():
                return cover_path
            return None
        except Exception as e:
            logger.error(f"下载封面失败: {e}")
            return None

    # ==================== 排行榜功能 ====================

    async def get_week_ranking(self, page: int = 1) -> list[dict]:
        """
        获取周排行榜

        Args:
            page: 页码

        Returns:
            排行榜结果列表
        """
        if not self.is_available():
            return []

        try:
            option = self._get_option()
            if option is None:
                return []

            return await self._run_sync(self._get_week_ranking_sync, page, option)
        except Exception as e:
            logger.error(f"获取周排行榜失败: {e}")
            return []

    def _get_week_ranking_sync(self, page: int, option) -> list[dict]:
        """同步获取周排行榜"""
        try:
            client = option.build_jm_client()
            ranking_page = client.week_ranking(page)

            results = []
            for album_id, title in ranking_page.iter_id_title():
                results.append(
                    {
                        "id": album_id,
                        "title": title,
                        "author": "",
                        "tags": [],
                        "category": "",
                    }
                )
            return results
        except Exception as e:
            logger.error(f"获取周排行榜失败: {e}")
            return []

    async def get_month_ranking(self, page: int = 1) -> list[dict]:
        """
        获取月排行榜

        Args:
            page: 页码

        Returns:
            排行榜结果列表
        """
        if not self.is_available():
            return []

        try:
            option = self._get_option()
            if option is None:
                return []

            return await self._run_sync(self._get_month_ranking_sync, page, option)
        except Exception as e:
            logger.error(f"获取月排行榜失败: {e}")
            return []

    def _get_month_ranking_sync(self, page: int, option) -> list[dict]:
        """同步获取月排行榜"""
        try:
            client = option.build_jm_client()
            ranking_page = client.month_ranking(page)

            results = []
            for album_id, title in ranking_page.iter_id_title():
                results.append(
                    {
                        "id": album_id,
                        "title": title,
                        "author": "",
                        "tags": [],
                        "category": "",
                    }
                )
            return results
        except Exception as e:
            logger.error(f"获取月排行榜失败: {e}")
            return []

    # ==================== 分类浏览功能 ====================

    # 分类常量映射
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

    # 排序常量映射
    ORDER_MAP = {
        "new": "mr",  # 最新
        "hot": "mv",  # 最热（观看数）
        "pic": "mp",  # 图片多
        "like": "tf",  # 点赞多
    }

    # 时间常量映射
    TIME_MAP = {
        "day": "t",  # 今日
        "week": "w",  # 本周
        "month": "m",  # 本月
        "all": "a",  # 全部时间
    }

    async def get_category_albums(
        self,
        category: str = "all",
        order_by: str = "hot",
        time_range: str = "week",
        page: int = 1,
    ) -> list[dict]:
        """
        获取分类浏览结果

        Args:
            category: 分类类型 (all/doujin/single/short/hanman/meiman/3d/cosplay/another)
            order_by: 排序方式 (new/hot/pic/like)
            time_range: 时间范围 (day/week/month/all)
            page: 页码

        Returns:
            漫画列表
        """
        if not self.is_available():
            return []

        try:
            option = self._get_option()
            if option is None:
                return []

            # 转换参数
            cat = self.CATEGORY_MAP.get(category.lower(), "0")
            order = self.ORDER_MAP.get(order_by.lower(), "mv")
            time = self.TIME_MAP.get(time_range.lower(), "w")

            return await self._run_sync(
                self._get_category_albums_sync, page, time, cat, order, option
            )
        except Exception as e:
            logger.error(f"获取分类浏览失败: {e}")
            return []

    def _get_category_albums_sync(
        self, page: int, time: str, category: str, order_by: str, option
    ) -> list[dict]:
        """同步获取分类浏览结果"""
        try:
            client = option.build_jm_client()
            category_page = client.categories_filter(
                page=page,
                time=time,
                category=category,
                order_by=order_by,
            )

            results = []
            for album_id, title in category_page.iter_id_title():
                results.append(
                    {
                        "id": album_id,
                        "title": title,
                        "author": "",
                        "tags": [],
                        "category": category,
                    }
                )
            return results
        except Exception as e:
            logger.error(f"获取分类浏览失败: {e}")
            return []

    @classmethod
    def get_category_list(cls) -> list[str]:
        """获取所有支持的分类"""
        return list(cls.CATEGORY_MAP.keys())

    @classmethod
    def get_order_list(cls) -> list[str]:
        """获取所有支持的排序方式"""
        return list(cls.ORDER_MAP.keys())

    @classmethod
    def get_time_list(cls) -> list[str]:
        """获取所有支持的时间范围"""
        return list(cls.TIME_MAP.keys())

    # ==================== 收藏夹功能 ====================

    async def get_favorites(
        self, client, page: int = 1, folder_id: str = "0"
    ) -> tuple[list[dict], list[dict]]:
        """
        获取收藏夹内容

        Args:
            client: 已登录的客户端
            page: 页码
            folder_id: 收藏夹ID，默认为 "0"（全部收藏）

        Returns:
            (收藏列表, 收藏夹列表)
        """
        if not self.is_available():
            return [], []

        try:
            return await self._run_sync(
                self._get_favorites_sync, client, page, folder_id
            )
        except Exception as e:
            logger.error(f"获取收藏夹失败: {e}")
            return [], []

    def _get_favorites_sync(
        self, client, page: int, folder_id: str
    ) -> tuple[list[dict], list[dict]]:
        """同步获取收藏夹内容"""
        try:
            fav_page = client.favorite_folder(page=page, folder_id=folder_id)

            # 获取收藏的本子
            albums = []
            for album_id, title in fav_page.iter_id_title():
                albums.append(
                    {
                        "id": album_id,
                        "title": title,
                    }
                )

            # 获取收藏夹列表
            folders = []
            for folder_id, folder_name in fav_page.iter_folder_id_name():
                folders.append(
                    {
                        "id": folder_id,
                        "name": folder_name,
                    }
                )

            return albums, folders
        except Exception as e:
            logger.error(f"获取收藏夹失败: {e}")
            return [], []
