"""
JMComic 下载管理模块

专注于下载功能：下载本子、下载章节。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .base import JMClientMixin, JMConfigManager
from .errors import classify_exception
from .jmcomic_loader import import_jmcomic, is_jmcomic_available

if TYPE_CHECKING:
    from jmcomic import JmOption

JMCOMIC_AVAILABLE = is_jmcomic_available()


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
    # 下载完整性：all_success 为 False 表示有图片/章节未成功下载
    all_success: bool = True
    failed_images: int = 0


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
        self,
        album_id: str,
        option: JmOption,
        progress_callback: Callable | None = None,
    ) -> DownloadResult:
        """同步下载本子（在线程池中执行）"""
        try:
            jmcomic = import_jmcomic()
            if jmcomic is None:
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

            parsed_id = jmcomic.JmcomicText.parse_to_jm_id(album_id)
            # check_exception=False: 让部分图片失败不抛异常，由下方读取下载器统计
            album, downloader = jmcomic.download_album(
                parsed_id, option, check_exception=False
            )

            save_path = Path(option.dir_rule.decide_album_root_dir(album))

            failed_images = len(getattr(downloader, "download_failed_image", []))
            failed_images += len(getattr(downloader, "download_failed_photo", []))
            all_success = bool(getattr(downloader, "all_success", True))

            return DownloadResult(
                success=True,
                album_id=str(album.id),
                title=album.title,
                author=album.author,
                photo_count=len(album),
                image_count=album.page_count,
                save_path=save_path,
                all_success=all_success,
                failed_images=failed_images,
            )

        except Exception as e:
            _, friendly = classify_exception(e)
            return DownloadResult(
                success=False,
                album_id=album_id,
                title="",
                author="",
                photo_count=0,
                image_count=0,
                save_path=Path(),
                error_message=friendly,
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
            jmcomic = import_jmcomic()
            if jmcomic is None:
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

            parsed_id = jmcomic.JmcomicText.parse_to_jm_id(photo_id)
            photo, downloader = jmcomic.download_photo(
                parsed_id, option, check_exception=False
            )

            save_path = Path(option.decide_image_save_dir(photo))
            image_count = len(photo.images) if hasattr(photo, "images") else 0

            failed_images = len(getattr(downloader, "download_failed_image", []))
            failed_images += len(getattr(downloader, "download_failed_photo", []))
            all_success = bool(getattr(downloader, "all_success", True))

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
                all_success=all_success,
                failed_images=failed_images,
            )

        except Exception as e:
            _, friendly = classify_exception(e)
            return DownloadResult(
                success=False,
                album_id=photo_id,
                title="",
                author="",
                photo_count=0,
                image_count=0,
                save_path=Path(),
                error_message=friendly,
            )
