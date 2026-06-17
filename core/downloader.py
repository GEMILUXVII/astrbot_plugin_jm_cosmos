"""
JMComic 下载管理模块

专注于下载功能：下载本子、下载章节。
"""

from __future__ import annotations

import asyncio
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

_PROGRESS_DOWNLOADER_CLASS = None


def _get_progress_downloader_class(jmcomic):
    """惰性构建一个带进度计数的 JmDownloader 子类（jmcomic 可用时才能定义）。"""
    global _PROGRESS_DOWNLOADER_CLASS
    if _PROGRESS_DOWNLOADER_CLASS is not None:
        return _PROGRESS_DOWNLOADER_CLASS

    class _ProgressDownloader(jmcomic.JmDownloader):
        """记录已下载图片数与总数，供上层轮询展示进度。"""

        def __init__(self, option):
            super().__init__(option)
            self.total_images = 0
            self.downloaded_images = 0
            self.skip_photos = 0  # 增量下载时跳过的前置章节数

        def create_client(self):
            # 每个下载使用独立 client，避免与其他并发操作共享状态
            return self.option.new_jm_client()

        def do_filter(self, detail):
            # 增量下载：仅对本子跳过前 skip_photos 个章节，其余不过滤
            if self.skip_photos and detail.is_album():
                return list(detail)[self.skip_photos :]
            return detail

        def before_album(self, album):
            super().before_album(album)
            try:
                self.total_images = album.page_count
            except Exception:
                pass

        def before_photo(self, photo):
            super().before_photo(photo)
            # 单章下载没有 album，用章节图片数作为总数
            if not self.total_images:
                try:
                    self.total_images = len(photo)
                except Exception:
                    pass

        def after_image(self, image, img_save_path):
            super().after_image(image, img_save_path)
            self.downloaded_images += 1

    _PROGRESS_DOWNLOADER_CLASS = _ProgressDownloader
    return _PROGRESS_DOWNLOADER_CLASS


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
        progress_callback: Callable[[int, int], Any] | None = None,
        skip_photos: int = 0,
    ) -> DownloadResult:
        """
        异步下载本子

        Args:
            album_id: 本子ID
            progress_callback: 进度回调协程 (current, total)，按 25% 步进调用
            skip_photos: 跳过前 N 个章节（用于增量下载新章节）

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

            return await self._run_with_progress(
                self._download_album_sync,
                (album_id, option, skip_photos),
                progress_callback,
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

    def _download_album_sync(
        self,
        album_id: str,
        option: JmOption,
        skip_photos: int = 0,
        progress_holder: dict | None = None,
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
            downloader_cls = _get_progress_downloader_class(jmcomic)
            downloader = downloader_cls(option)
            downloader.skip_photos = max(0, int(skip_photos))
            # 暴露下载器实例供上层轮询进度
            if progress_holder is not None:
                progress_holder["downloader"] = downloader

            # 直接驱动下载器（不使用 check_exception），部分失败由下方统计读取
            with downloader:
                album = downloader.download_album(parsed_id)

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
        progress_callback: Callable[[int, int], Any] | None = None,
    ) -> DownloadResult:
        """
        异步下载章节

        Args:
            photo_id: 章节ID
            progress_callback: 进度回调协程 (current, total)

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

            return await self._run_with_progress(
                self._download_photo_sync, (photo_id, option), progress_callback
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

    def _download_photo_sync(
        self,
        photo_id: str,
        option: JmOption,
        progress_holder: dict | None = None,
    ) -> DownloadResult:
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
            downloader_cls = _get_progress_downloader_class(jmcomic)
            downloader = downloader_cls(option)
            if progress_holder is not None:
                progress_holder["downloader"] = downloader

            with downloader:
                photo = downloader.download_photo(parsed_id)

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

    async def _run_with_progress(
        self,
        sync_func: Callable[..., DownloadResult],
        args: tuple,
        progress_callback: Callable[[int, int], Any] | None,
    ) -> DownloadResult:
        """在线程池执行同步下载，并按需轮询下载器进度回调上层。"""
        progress_holder: dict = {}
        task = asyncio.create_task(self._run_sync(sync_func, *args, progress_holder))
        if progress_callback is not None:
            await self._poll_progress(task, progress_holder, progress_callback)
        return await task

    @staticmethod
    async def _poll_progress(
        task: asyncio.Task,
        progress_holder: dict,
        progress_callback: Callable[[int, int], Any],
        interval: float = 2.0,
    ) -> None:
        """轮询下载器的图片计数，按 25% 步进回调进度（避免刷屏）。"""
        last_bucket = -1
        while not task.done():
            await asyncio.sleep(interval)
            downloader = progress_holder.get("downloader")
            if downloader is None:
                continue
            total = getattr(downloader, "total_images", 0)
            done = getattr(downloader, "downloaded_images", 0)
            if total <= 0 or done <= 0 or done >= total:
                continue
            bucket = int(done * 4 / total)
            if bucket != last_bucket:
                last_bucket = bucket
                try:
                    await progress_callback(done, total)
                except Exception:
                    pass
