"""
JMComic 浏览查询模块

提供搜索、详情查看、排行榜等浏览功能。
"""

from astrbot.api import logger

try:
    from jmcomic import JmcomicText

    JMCOMIC_AVAILABLE = True
except ImportError:
    JMCOMIC_AVAILABLE = False

from .client import JMClientMixin
from .config import JMConfigManager


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
