"""
JMComic 下载管理模块
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import jmcomic
    from jmcomic import (
        JmAlbumDetail,
        JmcomicText,
        JmOption,
        JmPhotoDetail,
    )

    JMCOMIC_AVAILABLE = True
except ImportError:
    JMCOMIC_AVAILABLE = False
    JmAlbumDetail = None
    JmPhotoDetail = None

from .config import JMConfigManager


@dataclass
class DownloadResult:
    """下载结果"""

    success: bool
    album_id: str
    title: str
    author: str
    photo_count: int
    image_count: int
    save_path: Path
    cover_path: Path | None = None
    error_message: str | None = None


class JMDownloadManager:
    """JMComic 下载管理器"""

    def __init__(self, config_manager: JMConfigManager):
        """
        初始化下载管理器

        Args:
            config_manager: 配置管理器实例
        """
        self.config = config_manager
        self._current_progress = {}

    async def download_album(
        self,
        album_id: str,
        progress_callback: Callable[[str, int, int], Any] | None = None,
    ) -> DownloadResult:
        """
        异步下载本子

        Args:
            album_id: 本子ID
            progress_callback: 进度回调函数 (status, current, total)

        Returns:
            DownloadResult 下载结果
        """
        if not JMCOMIC_AVAILABLE:
            return DownloadResult(
                success=False,
                album_id=album_id,
                title="",
                author="",
                photo_count=0,
                image_count=0,
                save_path=Path(),
                error_message="jmcomic 库未安装",
            )

        try:
            # 获取配置
            option = self.config.get_option()
            if option is None:
                return DownloadResult(
                    success=False,
                    album_id=album_id,
                    title="",
                    author="",
                    photo_count=0,
                    image_count=0,
                    save_path=Path(),
                    error_message="无法创建下载配置",
                )

            # 在线程池中执行同步下载
            result = await asyncio.to_thread(
                self._download_album_sync, album_id, option, progress_callback
            )
            return result

        except Exception as e:
            return DownloadResult(
                success=False,
                album_id=album_id,
                title="",
                author="",
                photo_count=0,
                image_count=0,
                save_path=Path(),
                error_message=str(e),
            )

    def _download_album_sync(
        self, album_id: str, option: JmOption, progress_callback: Callable | None = None
    ) -> DownloadResult:
        """同步下载本子（在线程池中执行）"""
        try:
            # 解析ID
            parsed_id = JmcomicText.parse_to_jm_id(album_id)

            # 执行下载
            album, downloader = jmcomic.download_album(parsed_id, option)

            # 获取保存路径
            save_path = Path(option.dir_rule.decide_album_root_dir(album))

            # 尝试获取封面路径
            cover_path = None
            if album.photo_count > 0:
                first_photo = album[0]
                if hasattr(first_photo, "images") and len(first_photo.images) > 0:
                    first_image = first_photo.images[0]
                    cover_path = Path(option.decide_image_filepath(first_image))

            # 统计图片数量
            total_images = sum(
                len(photo.images) if hasattr(photo, "images") else 0 for photo in album
            )

            return DownloadResult(
                success=True,
                album_id=str(album.id),
                title=album.title,
                author=album.author,
                photo_count=album.photo_count,
                image_count=total_images,
                save_path=save_path,
                cover_path=cover_path,
            )

        except Exception as e:
            return DownloadResult(
                success=False,
                album_id=album_id,
                title="",
                author="",
                photo_count=0,
                image_count=0,
                save_path=Path(),
                error_message=str(e),
            )

    async def download_photo(
        self,
        photo_id: str,
        progress_callback: Callable[[str, int, int], Any] | None = None,
    ) -> DownloadResult:
        """
        异步下载章节

        Args:
            photo_id: 章节ID
            progress_callback: 进度回调函数

        Returns:
            DownloadResult 下载结果
        """
        if not JMCOMIC_AVAILABLE:
            return DownloadResult(
                success=False,
                album_id=photo_id,
                title="",
                author="",
                photo_count=0,
                image_count=0,
                save_path=Path(),
                error_message="jmcomic 库未安装",
            )

        try:
            option = self.config.get_option()
            if option is None:
                return DownloadResult(
                    success=False,
                    album_id=photo_id,
                    title="",
                    author="",
                    photo_count=0,
                    image_count=0,
                    save_path=Path(),
                    error_message="无法创建下载配置",
                )

            result = await asyncio.to_thread(
                self._download_photo_sync, photo_id, option
            )
            return result

        except Exception as e:
            return DownloadResult(
                success=False,
                album_id=photo_id,
                title="",
                author="",
                photo_count=0,
                image_count=0,
                save_path=Path(),
                error_message=str(e),
            )

    def _download_photo_sync(self, photo_id: str, option: JmOption) -> DownloadResult:
        """同步下载章节"""
        try:
            parsed_id = JmcomicText.parse_to_jm_id(photo_id)
            photo, downloader = jmcomic.download_photo(parsed_id, option)

            # 获取保存路径
            save_path = Path(option.decide_image_save_dir(photo))

            # 获取图片数量
            image_count = len(photo.images) if hasattr(photo, "images") else 0

            return DownloadResult(
                success=True,
                album_id=str(photo.album_id)
                if hasattr(photo, "album_id")
                else photo_id,
                title=photo.title if hasattr(photo, "title") else "",
                author="",
                photo_count=1,
                image_count=image_count,
                save_path=save_path,
            )

        except Exception as e:
            return DownloadResult(
                success=False,
                album_id=photo_id,
                title="",
                author="",
                photo_count=0,
                image_count=0,
                save_path=Path(),
                error_message=str(e),
            )

    async def get_album_detail(self, album_id: str) -> dict | None:
        """
        获取本子详情

        Args:
            album_id: 本子ID

        Returns:
            本子详情字典
        """
        if not JMCOMIC_AVAILABLE:
            return None

        try:
            option = self.config.get_option()
            if option is None:
                return None

            result = await asyncio.to_thread(
                self._get_album_detail_sync, album_id, option
            )
            return result
        except Exception:
            return None

    def _get_album_detail_sync(self, album_id: str, option: JmOption) -> dict | None:
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
                "photo_count": album.photo_count,
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
        except Exception:
            return None

    async def search_albums(self, keyword: str, page: int = 1) -> list[dict]:
        """
        搜索本子

        Args:
            keyword: 搜索关键词
            page: 页码

        Returns:
            搜索结果列表
        """
        if not JMCOMIC_AVAILABLE:
            return []

        try:
            option = self.config.get_option()
            if option is None:
                return []

            result = await asyncio.to_thread(
                self._search_albums_sync, keyword, page, option
            )
            return result
        except Exception:
            return []

    def _search_albums_sync(
        self, keyword: str, page: int, option: JmOption
    ) -> list[dict]:
        """同步搜索本子"""
        try:
            client = option.build_jm_client()
            search_page = client.search_album(keyword, page)

            results = []
            for album in search_page:
                results.append(
                    {
                        "id": album.id,
                        "title": album.title,
                        "author": album.author if hasattr(album, "author") else "",
                        "tags": album.tags if hasattr(album, "tags") else [],
                        "category": album.category
                        if hasattr(album, "category")
                        else "",
                    }
                )
            return results
        except Exception:
            return []
