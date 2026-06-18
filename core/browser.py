"""
JMComic 浏览查询模块

提供搜索、详情查看、排行榜等浏览功能。
"""

from pathlib import Path

from astrbot.api import logger

from .base import JMClientMixin, JMConfigManager
from .constants import (
    CATEGORY_MAP,
    ORDER_MAP,
    TIME_MAP,
    get_category_list,
    get_order_list,
    get_time_list,
)
from .jmcomic_loader import import_jmcomic, is_jmcomic_available

JMCOMIC_AVAILABLE = is_jmcomic_available()


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

    async def search_albums(
        self, keyword: str, page: int = 1, mode: str = "site"
    ) -> list[dict]:
        """
        搜索本子

        Args:
            keyword: 搜索关键词
            page: 页码
            mode: 搜索模式 (site/tag/author/actor/work)

        Returns:
            搜索结果列表

        Raises:
            异常会向上传播，便于上层用 classify_exception 区分网络/未找到等原因
        """
        if not self.is_available():
            return []

        option = self._get_option()
        if option is None:
            return []

        return await self._run_sync(
            self._search_albums_sync, keyword, page, mode, option
        )

    def _search_albums_sync(
        self, keyword: str, page: int, mode: str, option
    ) -> list[dict]:
        """同步搜索本子（异常向上传播）"""
        client = option.new_jm_client()
        search_method = {
            "site": client.search_site,
            "tag": client.search_tag,
            "author": client.search_author,
            "actor": client.search_actor,
            "work": client.search_work,
        }.get(mode, client.search_site)
        search_page = search_method(keyword, page)

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

    # ==================== 详情功能 ====================

    async def get_album_detail(self, album_id: str) -> dict | None:
        """
        获取本子详情

        Args:
            album_id: 本子ID

        Returns:
            本子详情字典

        Raises:
            异常会向上传播，便于上层区分网络失败与本子不存在
        """
        if not self.is_available():
            return None

        option = self._get_option()
        if option is None:
            return None

        return await self._run_sync(self._get_album_detail_sync, album_id, option)

    def _get_album_detail_sync(self, album_id: str, option) -> dict | None:
        """同步获取本子详情（异常向上传播）"""
        jmcomic = import_jmcomic()
        if jmcomic is None:
            return None

        client = option.new_jm_client()
        parsed_id = jmcomic.JmcomicText.parse_to_jm_id(album_id)
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

        option = self._get_option()
        if option is None:
            return None

        return await self._run_sync(
            self._get_photo_id_by_index_sync, album_id, chapter_index, option
        )

    def _get_photo_id_by_index_sync(
        self, album_id: str, chapter_index: int, option
    ) -> tuple[str, str, int] | None:
        """同步获取章节ID（仅章节越界返回 None，其余异常向上传播以便归类）"""
        jmcomic = import_jmcomic()
        if jmcomic is None:
            return None

        client = option.new_jm_client()
        parsed_id = jmcomic.JmcomicText.parse_to_jm_id(album_id)
        album = client.get_album_detail(parsed_id)

        total_chapters = len(album.episode_list)

        # 仅章节序号越界视为“章节不存在”，返回 None（用户输入从1开始）
        if chapter_index < 1 or chapter_index > total_chapters:
            return None

        # 获取章节信息: (photo_id, photo_index, photo_title)
        photo_id, _, photo_title = album.episode_list[chapter_index - 1]

        return (photo_id, photo_title, total_chapters)

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
            jmcomic = import_jmcomic()
            if jmcomic is None:
                return None

            client = option.new_jm_client()
            parsed_id = jmcomic.JmcomicText.parse_to_jm_id(album_id)

            # 封面保存路径
            cover_path = save_dir / f"{parsed_id}.jpg"

            # 如果封面已存在，直接返回（缓存）
            if cover_path.exists():
                return cover_path

            # 下载封面
            client.download_album_cover(parsed_id, str(cover_path))

            if cover_path.exists():
                return cover_path
            return None
        except Exception as e:
            logger.error(f"下载封面失败: {e}")
            return None

    # ==================== 排行榜功能 ====================

    async def get_week_ranking(self, page: int = 1, category: str = "all") -> list[dict]:
        """
        获取周排行榜

        Args:
            page: 页码
            category: 分类类型 (all/doujin/hanman/...)

        Returns:
            排行榜结果列表
        """
        return await self._get_ranking("week", page, category)

    async def get_month_ranking(
        self, page: int = 1, category: str = "all"
    ) -> list[dict]:
        """
        获取月排行榜

        Args:
            page: 页码
            category: 分类类型 (all/doujin/hanman/...)

        Returns:
            排行榜结果列表
        """
        return await self._get_ranking("month", page, category)

    async def get_day_ranking(self, page: int = 1, category: str = "all") -> list[dict]:
        """
        获取日排行榜

        Args:
            page: 页码
            category: 分类类型 (all/doujin/hanman/...)

        Returns:
            排行榜结果列表
        """
        return await self._get_ranking("day", page, category)

    async def _get_ranking(
        self, ranking_type: str, page: int, category: str
    ) -> list[dict]:
        """排行榜统一入口：解析分类并在线程池中调用对应排行方法（异常向上传播）"""
        if not self.is_available():
            return []

        option = self._get_option()
        if option is None:
            return []

        cat = CATEGORY_MAP.get(category.lower(), "0")
        method_name = f"{ranking_type}_ranking"
        return await self._run_sync(
            self._get_ranking_sync, method_name, page, cat, option
        )

    def _get_ranking_sync(
        self, method_name: str, page: int, category: str, option
    ) -> list[dict]:
        """同步获取排行榜（method_name 为 jmcomic 客户端的排行方法名，异常向上传播）"""
        client = option.new_jm_client()
        ranking_page = getattr(client, method_name)(page, category)

        results = []
        for album_id, title in ranking_page.iter_id_title():
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

    # ==================== 分类浏览功能 ====================

    # 常量映射已移至 constants.py

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

        option = self._get_option()
        if option is None:
            return []

        # 转换参数
        cat = CATEGORY_MAP.get(category.lower(), "0")
        order = ORDER_MAP.get(order_by.lower(), "mv")
        time = TIME_MAP.get(time_range.lower(), "w")

        return await self._run_sync(
            self._get_category_albums_sync, page, time, cat, order, option
        )

    def _get_category_albums_sync(
        self, page: int, time: str, category: str, order_by: str, option
    ) -> list[dict]:
        """同步获取分类浏览结果（异常向上传播）"""
        client = option.new_jm_client()
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

    # 辅助方法：使用 constants 模块中的函数
    get_category_list = staticmethod(get_category_list)
    get_order_list = staticmethod(get_order_list)
    get_time_list = staticmethod(get_time_list)

    # ==================== 收藏夹功能 ====================

    async def get_favorites(
        self, client, page: int = 1, folder_id: str = "0", username: str = ""
    ) -> tuple[list[dict], list[dict]]:
        """
        获取收藏夹内容

        Args:
            client: 已登录的客户端
            page: 页码
            folder_id: 收藏夹ID，默认为 "0"（全部收藏）
            username: 登录用户名。HTML 客户端的 favorite_folder 需要它来拼接
                /user/<name>/favorite/albums，否则会抛“需要传username参数”；
                API 客户端忽略该参数（用会话）。每次新建的 client 不带 _username，
                故必须由上层（已知当前登录用户）显式传入。

        Returns:
            (收藏列表, 收藏夹列表)
        """
        if not self.is_available():
            return [], []

        return await self._run_sync(
            self._get_favorites_sync, client, page, folder_id, username
        )

    def _get_favorites_sync(
        self, client, page: int, folder_id: str, username: str = ""
    ) -> tuple[list[dict], list[dict]]:
        """同步获取收藏夹内容（异常向上传播）"""
        fav_page = client.favorite_folder(
            page=page, folder_id=folder_id, username=username
        )

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
        for fid, folder_name in fav_page.iter_folder_id_name():
            folders.append(
                {
                    "id": fid,
                    "name": folder_name,
                }
            )

        return albums, folders

    async def add_favorite(
        self, client, album_id: str, folder_id: str = "0"
    ) -> tuple[bool, str]:
        """收藏指定本子（幂等：已收藏则提示无需重复添加）。

        Args:
            client: 已登录的客户端
            album_id: 本子ID
            folder_id: 收藏夹ID

        Returns:
            (成功与否, 消息)
        """
        if not self.is_available():
            return False, "jmcomic 库未安装"

        try:
            return await self._run_sync(
                self._set_favorite_sync, client, album_id, folder_id, True
            )
        except Exception as e:
            logger.error(f"收藏操作失败: {e}")
            return False, str(e) or type(e).__name__

    async def remove_favorite(
        self, client, album_id: str, folder_id: str = "0"
    ) -> tuple[bool, str]:
        """取消收藏指定本子（幂等：本就不在收藏夹则提示无需取消）。

        Args:
            client: 已登录的客户端
            album_id: 本子ID
            folder_id: 收藏夹ID

        Returns:
            (成功与否, 消息)
        """
        if not self.is_available():
            return False, "jmcomic 库未安装"

        try:
            return await self._run_sync(
                self._set_favorite_sync, client, album_id, folder_id, False
            )
        except Exception as e:
            logger.error(f"取消收藏操作失败: {e}")
            return False, str(e) or type(e).__name__

    def _set_favorite_sync(
        self, client, album_id: str, folder_id: str, want_favorite: bool
    ) -> tuple[bool, str]:
        """同步设置收藏状态（幂等）。

        want_favorite=True 表示确保“已收藏”，False 表示确保“已取消”。

        踩过的坑：
        1) 会话隔离：插件默认走 API（移动端）登录，得到的会话(AVS)只对 API 端
           有效。早期用 HTML 客户端的 /ajax/favorite_album 会被服务端判为“未登录”，
           返回空响应导致失败且错误信息为空。因此必须复用登录所用的同一客户端。
        2) jmcomic 的 JmApiClient.add_favorite_album 以 GET 请求 /favorite（等同
           “列收藏”，响应无 status 字段，触发 KeyError('status')），故 API 端绕过
           它直接 POST /favorite。
        3) /favorite 与 /ajax/favorite_album 都是“切换(toggle)”：对已是目标状态
           的本子再调一次会反向。为此 API 端先用 /album 的 is_favorite 判断，仅当
           当前状态与目标不一致时才切换，避免“点添加反而取消”。
        """
        try:
            jmcomic = import_jmcomic()
            if jmcomic is None:
                return False, "jmcomic 库未安装"

            # 复用登录所用的客户端（携带有效会话）；缺省时按配置新建
            if client is None:
                option = self._get_option()
                if option is None:
                    return False, "无法创建下载配置"
                client = option.new_jm_client()

            parsed_id = jmcomic.JmcomicText.parse_to_jm_id(album_id)
            client_key = getattr(type(client), "client_key", "api")

            if client_key == "html":
                # 网页端无 is_favorite 预检，直接切换（best-effort）；失败会抛带 msg 的异常
                client.add_favorite_album(parsed_id, folder_id)
                if want_favorite:
                    return True, f"收藏成功（本子 {album_id}）"
                return True, f"已切换收藏状态（本子 {album_id}）"

            # API（移动端）：先查当前是否已收藏，规避 /favorite 的 toggle 误操作
            current = self._is_favorite_api(client, parsed_id)
            if current is True and want_favorite:
                return True, f"本子 {album_id} 已在收藏夹中，无需重复添加"
            if current is False and not want_favorite:
                return True, f"本子 {album_id} 不在收藏夹中，无需取消"

            # 当前状态与目标不一致（或无法查询）→ POST /favorite 切换
            # （GET /favorite 是“列收藏”，必须 POST）
            resp = client.req_api("/favorite", False, data={"aid": parsed_id})
            data = resp.model_data
            src = (
                data.src_dict
                if hasattr(data, "src_dict")
                else (data if isinstance(data, dict) else {})
            )
            status = src.get("status")
            server_msg = (src.get("msg") or "").strip()
            if status == "ok":
                default = (
                    f"收藏成功（本子 {album_id}）"
                    if want_favorite
                    else f"已取消收藏（本子 {album_id}）"
                )
                return True, server_msg or default
            action = "收藏" if want_favorite else "取消收藏"
            return False, server_msg or f"{action}失败（status={status}）"
        except Exception as e:
            logger.error(f"收藏操作失败: {e}")
            return False, str(e) or type(e).__name__

    @staticmethod
    def _is_favorite_api(client, parsed_id) -> bool | None:
        """查询当前登录账号是否已收藏该本子。

        读取 API /album 响应里的 is_favorite 字段（按登录账号返回）。
        返回 True/False；查询失败返回 None，调用方据此回退到直接切换。
        """
        try:
            resp = client.req_api("/album", params={"id": parsed_id})
            data = resp.model_data
            src = (
                data.src_dict
                if hasattr(data, "src_dict")
                else (data if isinstance(data, dict) else {})
            )
            return bool(src.get("is_favorite"))
        except Exception:
            return None
