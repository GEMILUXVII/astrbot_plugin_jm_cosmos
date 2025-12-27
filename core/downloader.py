"""
JMComic 下载管理模块

专注于下载功能：下载本子、下载章节。
"""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import jmcomic
    from jmcomic import (
        JmcomicText,
        JmOption,
    )

    JMCOMIC_AVAILABLE = True
except ImportError:
    JMCOMIC_AVAILABLE = False

from .base import JMClientMixin, JMConfigManager


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


class JMDownloadManager(JMClientMixin):
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
        if not self.is_available():
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
            option = self._get_option()
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

            return await self._run_sync(
                self._download_album_sync, album_id, option, progress_callback
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

    def _download_album_sync(
        self, album_id: str, option: JmOption, progress_callback: Callable | None = None
    ) -> DownloadResult:
        """同步下载本子（在线程池中执行）"""
        try:
            parsed_id = JmcomicText.parse_to_jm_id(album_id)
            album, downloader = jmcomic.download_album(parsed_id, option)

            save_path = Path(option.dir_rule.decide_album_root_dir(album))

            cover_path = None
            if len(album) > 0:
                first_photo = album[0]
                if hasattr(first_photo, "page_arr") and len(first_photo.page_arr) > 0:
                    cover_path = save_path

            return DownloadResult(
                success=True,
                album_id=str(album.id),
                title=album.title,
                author=album.author,
                photo_count=len(album),
                image_count=album.page_count,
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
        if not self.is_available():
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
            option = self._get_option()
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

            return await self._run_sync(self._download_photo_sync, photo_id, option)

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

            save_path = Path(option.decide_image_save_dir(photo))
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
