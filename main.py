from astrbot.api.message_components import Image, Plain
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register, StarTools
from astrbot.api import logger

import asyncio
import os
import glob
import random
import yaml
import re
import json
import traceback
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import time
import concurrent.futures
from threading import Lock

import jmcomic
from jmcomic import JmMagicConstants


# 添加自定义解析函数用于处理jmcomic库无法解析的情况
def extract_title_from_html(html_content: str) -> str:
    """从HTML内容中提取标题的多种尝试方法"""
    # 使用多种模式进行正则匹配
    patterns = [
        r"<h1[^>]*>([^<]+)</h1>",
        r"<title>([^<]+)</title>",
        r'name:\s*[\'"]([^\'"]+)[\'"]',
        r'"name":\s*"([^"]+)"',
        r'data-title=[\'"]([^\'"]+)[\'"]',
    ]

    for pattern in patterns:
        matches = re.findall(pattern, html_content)
        if matches:
            title = matches[0].strip()
            logger.info(f"已使用备用解析方法找到标题: {title}")
            return title

    return "未知标题"


def validate_comic_id(comic_id: str) -> bool:
    """验证漫画ID格式，防止路径遍历"""
    if not re.match(r"^\d+$", comic_id):
        return False
    if len(comic_id) > 10:  # 合理的ID长度限制
        return False
    return True


def validate_domain(domain: str) -> bool:
    """验证域名格式"""
    # 基本域名格式验证
    pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
    if not re.match(pattern, domain):
        return False
    if len(domain) > 253:
        return False
    # 防止添加恶意域名
    blocked_domains = ["localhost", "127.0.0.1", "0.0.0.0"]
    return domain not in blocked_domains


def handle_download_error(error: Exception, context: str) -> str:
    """统一的错误处理"""
    error_msg = str(error)

    if "timeout" in error_msg.lower():
        return f"{context}超时，请检查网络连接或稍后重试"
    elif "connection" in error_msg.lower():
        return f"{context}连接失败，请检查网络或代理设置"
    elif "文本没有匹配上字段" in error_msg:
        return f"{context}失败：网站结构可能已更改，请使用 /jmdomain update 更新域名"
    elif "permission" in error_msg.lower() or "access" in error_msg.lower():
        return f"{context}失败：文件权限错误，请检查存储目录权限"
    elif "space" in error_msg.lower() or "disk" in error_msg.lower():
        return f"{context}失败：存储空间不足，请清理磁盘空间"
    else:
        logger.error(f"{context}未知错误: {error_msg}", exc_info=True)
        return f"{context}失败：{error_msg[:100]}"  # 限制错误消息长度


# 使用枚举定义下载状态
class DownloadStatus(Enum):
    SUCCESS = "成功"
    PENDING = "等待中"
    DOWNLOADING = "下载中"
    FAILED = "失败"


# 使用数据类来管理配置
@dataclass
class CosmosConfig:
    """Cosmos插件配置类"""

    domain_list: List[str]
    proxy: Optional[str]
    avs_cookie: str
    max_threads: int
    debug_mode: bool
    show_cover: bool

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "CosmosConfig":
        """从字典创建配置对象"""
        return cls(
            domain_list=config_dict.get(
                "domain_list", ["18comic.vip", "jm365.xyz", "18comic.org"]
            ),
            proxy=config_dict.get("proxy"),
            avs_cookie=config_dict.get("avs_cookie", ""),
            max_threads=config_dict.get("max_threads", 10),
            debug_mode=config_dict.get("debug_mode", False),
            show_cover=config_dict.get("show_cover", True),
        )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "domain_list": self.domain_list,
            "proxy": self.proxy,
            "avs_cookie": self.avs_cookie,
            "max_threads": self.max_threads,
            "debug_mode": self.debug_mode,
            "show_cover": self.show_cover,
        }

    @classmethod
    def load_from_file(cls, config_path: str) -> "CosmosConfig":
        """从文件加载配置"""
        default_config = cls(
            domain_list=["18comic.vip", "jm365.xyz", "18comic.org"],
            proxy=None,
            avs_cookie="",
            max_threads=10,
            debug_mode=False,
            show_cover=True,
        )

        if not os.path.exists(config_path):
            logger.warning(f"配置文件不存在，使用默认配置: {config_path}")
            return default_config

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_dict = yaml.safe_load(f)

            if not config_dict:
                logger.warning("配置文件为空，使用默认配置")
                return default_config

            return cls.from_dict(config_dict)
        except Exception as e:
            logger.error(f"加载配置文件失败: {str(e)}")
            return default_config

    def save_to_file(self, config_path: str) -> bool:
        """保存配置到文件"""
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(self.to_dict(), f, allow_unicode=True)
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {str(e)}")
            return False


class ResourceManager:
    """资源管理器，管理文件路径和创建必要的目录"""

    def __init__(self, plugin_name: str):
        # 使用StarTools获取数据目录
        self.base_dir = StarTools.get_data_dir(plugin_name)
        # 目录结构
        self.downloads_dir = os.path.join(self.base_dir, "downloads")
        self.pdfs_dir = os.path.join(self.base_dir, "pdfs")
        self.logs_dir = os.path.join(self.base_dir, "logs")
        self.temp_dir = os.path.join(self.base_dir, "temp")
        # 添加专门的封面目录
        self.covers_dir = os.path.join(self.base_dir, "covers")

        # 存储管理配置
        self.max_storage_size = 2 * 1024 * 1024 * 1024  # 2GB限制
        self.max_file_age_days = 30  # 文件保留30天

        # 创建必要的目录
        for dir_path in [
            self.downloads_dir,
            self.pdfs_dir,
            self.logs_dir,
            self.temp_dir,
            self.covers_dir,
        ]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)

    def check_storage_space(self) -> tuple[bool, int]:
        """检查存储空间使用情况"""
        total_size = 0
        try:
            for root, dirs, files in os.walk(self.base_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.exists(file_path):
                        total_size += os.path.getsize(file_path)
        except Exception as e:
            logger.error(f"计算存储空间时出错: {str(e)}")
            return False, 0

        return total_size < self.max_storage_size, total_size

    def cleanup_old_files(self) -> int:
        """清理超过指定天数的文件"""

        cutoff_time = time.time() - (self.max_file_age_days * 24 * 60 * 60)
        cleaned_count = 0

        try:
            for root, dirs, files in os.walk(self.base_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    if os.path.exists(file_path):
                        if os.path.getmtime(file_path) < cutoff_time:
                            try:
                                os.remove(file_path)
                                cleaned_count += 1
                                logger.info(f"清理过期文件: {file_path}")
                            except Exception as e:
                                logger.error(f"删除文件失败 {file_path}: {str(e)}")
        except Exception as e:
            logger.error(f"清理文件时出错: {str(e)}")

        return cleaned_count

    def get_storage_info(self) -> dict:
        """获取存储信息"""
        has_space, total_size = self.check_storage_space()
        return {
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "max_size_mb": round(self.max_storage_size / (1024 * 1024), 2),
            "has_space": has_space,
            "usage_percent": round((total_size / self.max_storage_size) * 100, 2),
        }

    def find_comic_folder(self, comic_id: str) -> str:
        """查找漫画文件夹，支持多种命名方式"""
        logger.info(f"开始查找漫画ID {comic_id} 的文件夹")

        # 尝试直接匹配ID
        id_path = os.path.join(self.downloads_dir, str(comic_id))
        if os.path.exists(id_path):
            logger.info(f"找到直接匹配的目录: {id_path}")
            return id_path

        # 尝试查找以漫画标题命名的目录
        if os.path.exists(self.downloads_dir):
            # 首先尝试查找以ID开头或结尾的目录名，或者格式为 [ID]_title 的目录
            exact_matches = []
            partial_matches = []

            for item in os.listdir(self.downloads_dir):
                item_path = os.path.join(self.downloads_dir, item)
                if not os.path.isdir(item_path):
                    continue

                # 精确匹配：目录名以ID开头或结尾，或者格式为 [ID]_title
                if (
                    item.startswith(str(comic_id) + "_")
                    or item.endswith("_" + str(comic_id))
                    or item.startswith("[" + str(comic_id) + "]")
                    or item == str(comic_id)
                ):
                    exact_matches.append(item_path)
                    logger.info(f"找到精确匹配的漫画目录: {item_path}")
                # 部分匹配：目录名包含ID但不是精确格式
                elif str(comic_id) in item:
                    # 进一步验证：确保是完整的ID匹配，而不是部分匹配
                    # 使用正则表达式确保ID是独立的数字
                    import re

                    pattern = r"\b" + re.escape(str(comic_id)) + r"\b"
                    if re.search(pattern, item):
                        partial_matches.append(item_path)
                        logger.info(f"找到部分匹配的漫画目录: {item_path}")

            # 优先返回精确匹配
            if exact_matches:
                logger.info(f"找到精确匹配，返回: {exact_matches[0]}")
                return exact_matches[0]
            elif partial_matches:
                logger.info(f"找到部分匹配，返回: {partial_matches[0]}")
                return partial_matches[0]

        # 默认返回downloads目录下的ID路径
        default_path = os.path.join(self.downloads_dir, str(comic_id))
        logger.info(f"未找到现有目录，返回默认路径: {default_path}")
        return default_path

    def get_comic_folder(self, comic_id: str) -> str:
        """获取漫画文件夹路径"""
        return self.find_comic_folder(comic_id)

    def get_cover_path(self, comic_id: str) -> str:
        """获取封面图片路径"""
        # 始终返回封面目录中对应ID的封面路径
        cover_path = os.path.join(self.covers_dir, f"{comic_id}.jpg")

        # 如果封面已存在则返回
        if os.path.exists(cover_path):
            file_size = os.path.getsize(cover_path)
            if file_size > 1000:  # 有效文件大小
                return cover_path
            else:
                # 文件过小，可能是空文件或损坏文件，删除它
                try:
                    os.remove(cover_path)
                    logger.warning(
                        f"删除无效封面文件: {cover_path}, 大小: {file_size}字节"
                    )
                except Exception:
                    pass

        # 返回封面目录中的预期路径
        return cover_path

    def get_pdf_path(self, comic_id: str) -> str:
        """获取PDF文件路径"""
        return os.path.join(self.pdfs_dir, f"{comic_id}.pdf")

    def get_log_path(self, prefix: str) -> str:
        """获取日志文件路径"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.logs_dir, f"{prefix}_{timestamp}.txt")

    def list_comic_images(self, comic_id: str, limit: int = None) -> List[str]:
        """获取漫画图片列表"""
        comic_folder = self.get_comic_folder(comic_id)
        if not os.path.exists(comic_folder):
            logger.warning(f"漫画目录不存在: {comic_folder}")
            return []

        logger.info(f"正在查找漫画图片，目录: {comic_folder}")
        image_files = []

        # 遍历目录结构寻找图片
        try:
            # 首先直接检查主目录下的图片
            direct_images = [
                os.path.join(comic_folder, f)
                for f in os.listdir(comic_folder)
                if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
                and os.path.isfile(os.path.join(comic_folder, f))
            ]

            if direct_images:
                # 主目录下有图片，直接使用
                image_files.extend(sorted(direct_images))
                logger.info(f"在主目录下找到 {len(direct_images)} 张图片")
            else:
                # 检查所有子目录
                sub_folders = []
                for item in os.listdir(comic_folder):
                    item_path = os.path.join(comic_folder, item)
                    if os.path.isdir(item_path):
                        sub_folders.append(item_path)

                # 按照目录名排序，确保图片顺序正确
                sub_folders.sort()

                # 从每个子目录收集图片
                for folder in sub_folders:
                    folder_images = []
                    for img in os.listdir(folder):
                        if img.lower().endswith(
                            (".jpg", ".jpeg", ".png", ".webp")
                        ) and os.path.isfile(os.path.join(folder, img)):
                            folder_images.append(os.path.join(folder, img))

                    # 确保每个文件夹内的图片按名称排序
                    folder_images.sort()
                    image_files.extend(folder_images)

                logger.info(f"在子目录中找到 {len(image_files)} 张图片")
        except Exception as e:
            logger.error(f"列出漫画图片时出错: {str(e)}")

        if not image_files:
            logger.warning(f"未找到任何图片文件，请检查目录: {comic_folder}")

        # 应用限制并返回结果
        return image_files[:limit] if limit else image_files

    def clear_cover_cache(self):
        """清理封面缓存目录"""
        if os.path.exists(self.covers_dir):
            logger.info(f"开始清理封面缓存目录: {self.covers_dir}")
            try:
                # 先列出所有文件
                count = 0
                for file in os.listdir(self.covers_dir):
                    file_path = os.path.join(self.covers_dir, file)
                    if os.path.isfile(file_path):
                        try:
                            os.remove(file_path)
                            count += 1
                        except Exception as e:
                            logger.error(
                                f"删除封面缓存文件失败: {file_path}, 错误: {str(e)}"
                            )
                logger.info(f"封面缓存清理完成，共删除 {count} 个文件")
                return count
            except Exception as e:
                logger.error(f"清理封面缓存目录失败: {str(e)}")
                return 0
        return 0


class JMClientFactory:
    """JM客户端工厂，负责创建和管理JM客户端实例"""

    def __init__(self, config: CosmosConfig, resource_manager: ResourceManager):
        self.config = config
        self.resource_manager = resource_manager
        self.option = self._create_option()

    def _create_option(self):
        """创建JM客户端选项"""
        option_dict = {
            "client": {
                "impl": "html",
                "domain": self.config.domain_list,
                "retry_times": 5,
                "postman": {
                    "meta_data": {
                        "proxies": {"https": self.config.proxy}
                        if self.config.proxy
                        else None,
                        "cookies": {"AVS": self.config.avs_cookie},
                        # 添加浏览器模拟的请求头
                        "headers": {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                            "Referer": f"https://{self.config.domain_list[0]}/",
                            "Connection": "keep-alive",
                            "Cache-Control": "max-age=0",
                        },
                    }
                },
            },
            "download": {
                "cache": True,
                "image": {"decode": True, "suffix": ".jpg"},
                "threading": {
                    "image": self.config.max_threads,
                    "photo": self.config.max_threads,
                },
            },
            "dir_rule": {"base_dir": self.resource_manager.downloads_dir},
            "plugins": {
                "after_album": [
                    {
                        "plugin": "img2pdf",
                        "kwargs": {
                            "pdf_dir": self.resource_manager.pdfs_dir,
                            "filename_rule": "Aid",
                        },
                    }
                ]
            },
        }
        yaml_str = yaml.safe_dump(option_dict, allow_unicode=True)
        return jmcomic.create_option_by_str(yaml_str)

    def create_client(self):
        """创建JM客户端"""
        return self.option.new_jm_client()

    def create_client_with_domain(self, domain: str):
        """创建使用特定域名的JM客户端"""
        custom_option = jmcomic.JmOption.default()
        custom_option.client.domain = [domain]
        custom_option.client.postman.meta_data = {
            "proxies": {"https": self.config.proxy} if self.config.proxy else None,
            "cookies": {"AVS": self.config.avs_cookie},
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Referer": f"https://{domain}/",
            },
        }
        return custom_option.new_jm_client()

    def update_option(self):
        """更新JM客户端选项"""
        self.option = self._create_option()


class ComicDownloader:
    """漫画下载器，负责下载漫画和封面"""

    def __init__(
        self,
        client_factory: JMClientFactory,
        resource_manager: ResourceManager,
        config: CosmosConfig,
    ):
        self.client_factory = client_factory
        self.resource_manager = resource_manager
        self.config = config
        self.downloading_comics: Set[str] = set()
        self.downloading_covers: Set[str] = set()
        self._download_lock = Lock()

        # 使用线程池替代无限制的线程创建
        self._thread_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=min(self.config.max_threads, 20),  # 限制最大线程数
            thread_name_prefix="jm_download",
        )

    def __del__(self):
        """确保线程池被正确关闭"""
        if hasattr(self, "_thread_pool"):
            self._thread_pool.shutdown(wait=True)

    async def download_cover(self, album_id: str) -> Tuple[bool, str]:
        """下载漫画封面"""
        if album_id in self.downloading_covers:
            return False, "封面正在下载中"

        self.downloading_covers.add(album_id)
        try:
            # 记录在对应ID下载封面
            logger.info(f"开始下载漫画封面，ID: {album_id}")

            client = self.client_factory.create_client()

            try:
                album = client.get_album_detail(album_id)
                if not album:
                    return False, "漫画不存在"

                # 记录漫画标题
                logger.info(f"获取到漫画信息，ID: {album_id}, 标题: {album.title}")

            except Exception as e:
                error_msg = str(e)
                logger.error(f"获取漫画详情失败: {error_msg}")

                if "文本没有匹配上字段" in error_msg and "pattern:" in error_msg:
                    # 尝试手动解析HTML
                    try:
                        html_content = client._postman.get_html(
                            f"https://{self.config.domain_list[0]}/album/{album_id}"
                        )
                        self._save_debug_info(f"album_html_{album_id}", html_content)

                        title = extract_title_from_html(html_content)
                        return (
                            False,
                            f"解析漫画信息失败，网站结构可能已更改，但找到了标题: {title}",
                        )
                    except Exception as parse_e:
                        return False, f"解析漫画信息失败: {str(parse_e)}"

                return False, f"获取漫画详情失败: {error_msg}"

            first_photo = album[0]
            photo = client.get_photo_detail(first_photo.photo_id, True)
            if not photo:
                return False, "章节内容为空"

            image = photo[0]

            # 使用独立的封面目录保存封面
            cover_path = os.path.join(
                self.resource_manager.covers_dir, f"{album_id}.jpg"
            )

            # 删除可能存在的旧封面，强制更新
            if os.path.exists(cover_path):
                try:
                    os.remove(cover_path)
                    logger.info(f"已删除旧封面: {cover_path}")
                except Exception as e:
                    logger.error(f"删除旧封面失败: {str(e)}")

            # 创建漫画文件夹 - 仍然需要创建这个目录，因为下载漫画时会用到
            comic_folder = self.resource_manager.get_comic_folder(album_id)
            os.makedirs(comic_folder, exist_ok=True)

            # 下载封面到封面专用目录
            logger.info(f"下载封面到: {cover_path}")
            client.download_by_image_detail(image, cover_path)

            # 验证封面是否已下载
            if os.path.exists(cover_path):
                file_size = os.path.getsize(cover_path)
                logger.info(f"封面下载成功: {cover_path}, 大小: {file_size} 字节")
                if file_size < 1000:  # 如果文件太小，可能下载失败
                    logger.warning(f"封面文件大小异常，可能下载失败: {file_size} 字节")
            else:
                logger.error(f"封面下载后未找到文件: {cover_path}")

            return True, cover_path
        except Exception as e:
            error_msg = str(e)
            logger.error(f"封面下载失败: {error_msg}")

            if "文本没有匹配上字段" in error_msg:
                return (
                    False,
                    "封面下载失败: 网站结构可能已更改，请更新jmcomic库或使用/jmdomain更新域名",
                )

            return False, f"封面下载失败: {error_msg}"
        finally:
            self.downloading_covers.discard(album_id)

    async def download_comic(self, album_id: str) -> Tuple[bool, Optional[str]]:
        """下载完整漫画"""
        with self._download_lock:
            if album_id in self.downloading_comics:
                return False, "该漫画正在下载中，请稍候"
            self.downloading_comics.add(album_id)

        try:
            # 检查存储空间
            has_space, _ = self.resource_manager.check_storage_space()
            if not has_space:
                # 尝试清理旧文件
                cleaned = self.resource_manager.cleanup_old_files()
                logger.info(f"存储空间不足，已清理 {cleaned} 个文件")

                # 重新检查
                has_space, _ = self.resource_manager.check_storage_space()
                if not has_space:
                    return False, "存储空间不足，请手动清理后重试"

            # 在debug模式下添加线程监控
            if self.config.debug_mode:
                import threading

                initial_threads = threading.active_count()
                logger.info(f"下载开始前活跃线程数: {initial_threads}")

            # 使用线程池执行下载
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._thread_pool, self._download_with_retry, album_id
            )

            # 在debug模式下记录最终线程数
            if self.config.debug_mode:
                import threading

                final_threads = threading.active_count()
                thread_diff = final_threads - initial_threads
                logger.info(f"下载结束时活跃线程数: {final_threads}")
                logger.info(f"下载过程中创建的线程数: {thread_diff}")

                # 列出所有线程名称
                current_threads = threading.enumerate()
                thread_names = [t.name for t in current_threads]
                logger.info(f"当前线程列表: {thread_names}")

                # 记录配置的最大线程数
                logger.info(f"配置的最大线程数: {self.config.max_threads}")

                # 保存调试信息到文件
                self._save_debug_info(
                    f"thread_info_{album_id}",
                    f"下载开始前线程数: {initial_threads}\n"
                    f"下载结束时线程数: {final_threads}\n"
                    f"下载过程中创建的线程数: {thread_diff}\n"
                    f"配置的最大线程数: {self.config.max_threads}\n"
                    f"当前线程列表: {thread_names}",
                )

            return result
        except Exception as e:
            logger.error(f"下载调度失败: {str(e)}")
            return False, f"下载调度失败: {str(e)}"
        finally:
            with self._download_lock:
                self.downloading_comics.discard(album_id)

    def _download_with_retry(self, album_id: str) -> Tuple[bool, Optional[str]]:
        """带重试功能的下载函数"""
        try:
            # 添加调试信息，显示当前使用的域名
            current_domains = self.config.domain_list
            logger.info(
                f"开始下载漫画 {album_id}，当前配置的域名列表: {current_domains}"
            )
            if current_domains:
                logger.info(f"主要使用域名: {current_domains[0]}")

            # 不使用全局 download_album 函数，而是直接使用 option 和客户端
            # 这样可以确保使用我们更新的配置
            option = self.client_factory.option
            logger.info(f"使用的option域名配置: {option.client.domain}")

            # 使用 option 直接下载，避免全局配置干扰
            try:
                client = self.client_factory.create_client()
                logger.info(
                    f"创建的客户端域名配置: {self.client_factory.option.client.domain}"
                )

                # 添加更多调试信息
                try:
                    # 先测试客户端是否能正常访问
                    import time

                    start_time = time.time()
                    album = client.get_album_detail(album_id)
                    end_time = time.time()
                    logger.info(
                        f"获取漫画详情成功，耗时: {end_time - start_time:.2f}秒"
                    )
                    logger.info(f"漫画标题: {getattr(album, 'name', '未知')}")

                    # 使用正确的下载方法 - 第一个参数应该是漫画ID，不是album对象
                    jmcomic.download_album(album_id, option)
                except Exception as detail_error:
                    error_detail = str(detail_error)
                    logger.error(f"获取漫画详情或下载失败: {error_detail}")

                    # 如果是因为漫画不存在，尝试用其他域名
                    if "请求的本子不存在" in error_detail or "不存在" in error_detail:
                        logger.info("尝试使用其他域名...")
                        for i, backup_domain in enumerate(
                            self.config.domain_list[1:3], 1
                        ):  # 尝试2-3个备用域名
                            try:
                                logger.info(f"尝试备用域名 {i}: {backup_domain}")
                                backup_client = (
                                    self.client_factory.create_client_with_domain(
                                        backup_domain
                                    )
                                )
                                album = backup_client.get_album_detail(album_id)
                                # 创建使用特定域名的临时option
                                backup_option = jmcomic.JmOption.default()
                                backup_option.client.domain = [backup_domain]
                                backup_option.dir_rule.base_dir = (
                                    option.dir_rule.base_dir
                                )
                                if self.config.proxy:
                                    backup_option.client.postman.meta_data = {
                                        "proxies": {"https": self.config.proxy}
                                    }
                                if self.config.avs_cookie:
                                    backup_option.client.postman.meta_data = (
                                        backup_option.client.postman.meta_data or {}
                                    )
                                    backup_option.client.postman.meta_data[
                                        "cookies"
                                    ] = {"AVS": self.config.avs_cookie}
                                jmcomic.download_album(album_id, backup_option)
                                logger.info(f"使用备用域名 {backup_domain} 下载成功")
                                break
                            except Exception as backup_error:
                                backup_error_msg = str(backup_error)
                                # 替换错误消息中的域名
                                backup_error_msg = backup_error_msg.replace(
                                    "18comic.vip", backup_domain
                                )
                                backup_error_msg = backup_error_msg.replace(
                                    "jmcomic.me", backup_domain
                                )
                                backup_error_msg = backup_error_msg.replace(
                                    "jm18c.cc", backup_domain
                                )
                                logger.warning(
                                    f"备用域名 {backup_domain} 也失败: {backup_error_msg}"
                                )
                                continue
                        else:
                            # 所有域名都失败了
                            raise detail_error
                    else:
                        raise detail_error

                # 如果启用了PDF转换，手动调用
                if hasattr(option, "plugins") and option.plugins:
                    for plugin_config in option.plugins.get("after_album", []):
                        if plugin_config.get("plugin") == "img2pdf":
                            import img2pdf
                            from pathlib import Path

                            # 查找下载的图片文件
                            album_dir = Path(option.dir_rule.base_dir) / str(album_id)
                            if album_dir.exists():
                                image_files = list(album_dir.glob("*.jpg")) + list(
                                    album_dir.glob("*.png")
                                )
                                if image_files:
                                    # 按文件名排序
                                    image_files.sort()
                                    pdf_path = (
                                        Path(plugin_config["kwargs"]["pdf_dir"])
                                        / f"{album_id}.pdf"
                                    )
                                    pdf_path.parent.mkdir(parents=True, exist_ok=True)

                                    with open(pdf_path, "wb") as f:
                                        f.write(
                                            img2pdf.convert(
                                                [str(img) for img in image_files]
                                            )
                                        )
                                    logger.info(f"已生成PDF: {pdf_path}")

                return True, None
            except Exception as client_error:
                # 如果直接使用客户端失败，回退到原方法
                logger.warning(f"直接使用客户端下载失败，回退到原方法: {client_error}")

                # 尝试最后的回退：强制使用第一个可用域名创建新的option
                try:
                    logger.info("尝试使用强制域名配置进行最后的回退...")
                    forced_option = jmcomic.JmOption.default()
                    forced_option.client.domain = [self.config.domain_list[0]]
                    if self.config.proxy:
                        forced_option.client.postman.meta_data = {
                            "proxies": {"https": self.config.proxy}
                        }
                    if self.config.avs_cookie:
                        forced_option.client.postman.meta_data = (
                            forced_option.client.postman.meta_data or {}
                        )
                        forced_option.client.postman.meta_data["cookies"] = {
                            "AVS": self.config.avs_cookie
                        }

                    jmcomic.download_album(album_id, forced_option)
                    logger.info("强制域名配置下载成功")
                except Exception as forced_error:
                    logger.error(f"强制域名配置也失败: {forced_error}")
                    # 最后的回退
                    jmcomic.download_album(album_id, self.client_factory.option)
                return True, None

        except Exception as e:
            error_msg = str(e)
            logger.error(f"下载失败: {error_msg}")

            # 保存错误堆栈
            stack_trace = traceback.format_exc()
            self._save_debug_info(f"download_error_{album_id}", stack_trace)

            # 将错误消息中的默认域名替换为我们实际使用的域名
            if self.config.domain_list and len(self.config.domain_list) > 0:
                actual_domain = self.config.domain_list[0]
                error_msg = error_msg.replace("18comic.vip", actual_domain)
                error_msg = error_msg.replace("jmcomic.me", actual_domain)
                error_msg = error_msg.replace("jm18c.cc", actual_domain)

            if "文本没有匹配上字段" in error_msg and "pattern:" in error_msg:
                try:
                    # 尝试手动解析
                    client = self.client_factory.create_client()
                    html_content = client._postman.get_html(
                        f"https://{self.config.domain_list[0]}/album/{album_id}"
                    )
                    self._save_debug_info(f"album_html_{album_id}", html_content)

                    return (
                        False,
                        "下载失败: 网站结构可能已更改，请更新jmcomic库或使用/jmdomain更新域名",
                    )
                except Exception:
                    pass

            return False, f"下载失败: {error_msg}"

    def _save_debug_info(self, prefix: str, content: str) -> None:
        """保存调试信息到文件"""
        if not self.config.debug_mode:
            return

        try:
            log_path = self.resource_manager.get_log_path(prefix)
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"已保存调试信息到 {log_path}")
        except Exception as e:
            logger.error(f"保存调试信息失败: {str(e)}")

    def get_total_pages(self, client, album) -> int:
        """获取漫画总页数"""
        try:
            return sum(len(client.get_photo_detail(p.photo_id, False)) for p in album)
        except Exception as e:
            logger.error(f"获取总页数失败: {str(e)}")
            return 0

    def preview_download_comic(
        self, client, comic_id: str, max_pages: int = 3
    ) -> tuple[bool, str, list]:
        """预览下载漫画前几页

        Args:
            client: JM客户端
            comic_id: 漫画ID
            max_pages: 最大预览页数，默认3页

        Returns:
            tuple: (成功状态, 消息, 图片路径列表)
        """
        preview_dir = None
        downloaded_images = []

        try:
            # 获取漫画详情
            album = client.get_album_detail(comic_id)
            if not album:
                return False, f"无法获取漫画 {comic_id} 的详情", []

            # 创建预览目录
            preview_dir = os.path.join(
                self.resource_manager.base_dir, "preview_downloads", f"{comic_id}"
            )
            os.makedirs(preview_dir, exist_ok=True)

            logger.info(f"开始预览下载漫画 {comic_id}，前 {max_pages} 页")

            page_count = 0
            for episode in album:
                if page_count >= max_pages:
                    break

                try:
                    photo_detail = client.get_photo_detail(episode.photo_id, False)
                    for photo in photo_detail:
                        if page_count >= max_pages:
                            break

                        # 下载图片
                        img_path = os.path.join(
                            preview_dir, f"page_{page_count + 1:03d}.jpg"
                        )

                        # 使用 jmcomic 的下载方法
                        try:
                            client.download_by_image_detail(photo, img_path)

                            # 验证下载是否成功
                            if (
                                os.path.exists(img_path)
                                and os.path.getsize(img_path) > 1000
                            ):
                                downloaded_images.append(img_path)
                                page_count += 1
                                logger.info(f"已下载预览页 {page_count}/{max_pages}")
                            else:
                                logger.warning(
                                    f"下载的图片文件太小或不存在: {img_path}"
                                )
                        except Exception as download_e:
                            logger.warning(f"下载图片失败: {str(download_e)}")
                            continue

                except Exception as e:
                    logger.error(f"下载章节 {episode.photo_id} 失败: {str(e)}")
                    continue

            if downloaded_images:
                return (
                    True,
                    f"预览下载完成，共 {len(downloaded_images)} 页",
                    downloaded_images,
                )
            else:
                return False, "预览下载失败，未获取到任何图片", []

        except Exception as e:
            logger.error(f"预览下载失败: {str(e)}")
            # 清理失败的下载
            if preview_dir and os.path.exists(preview_dir):
                try:
                    import shutil

                    shutil.rmtree(preview_dir)
                except Exception:
                    pass
            return False, f"预览下载失败: {str(e)}", []


@register(
    "jm_cosmos",
    "GEMILUXVII",
    "全能型JM漫画下载与管理工具",
    "1.1.0",
    "https://github.com/GEMILUXVII/astrbot_plugin_jm_cosmos",
)
class JMCosmosPlugin(Star):
    """Cosmos插件主类"""

    def __init__(self, context: Context, config=None):
        super().__init__(context)
        self.plugin_name = "jm_cosmos"
        self.base_path = os.path.realpath(os.path.dirname(__file__))

        # 详细日志记录
        logger.info(f"Cosmos插件初始化，配置参数: {config}")

        # 初始化组件 - 使用插件名初始化ResourceManager而不是目录路径
        self.resource_manager = ResourceManager(self.plugin_name)

        # 清理封面缓存
        logger.info("初始化时清理封面缓存")
        self.resource_manager.clear_cover_cache()

        # AstrBot配置文件路径
        self.astrbot_config_path = os.path.join(
            self.context.get_config().get("data_dir", "data"),
            "config",
            f"astrbot_plugin_{self.plugin_name}_config.json",
        )

        # 如果传入了AstrBot配置，使用它
        if config is not None:
            logger.info(f"使用AstrBot配置系统: {config}")

            # 获取domain_list，确保是列表
            domain_list = config.get(
                "domain_list", ["18comic.vip", "jm365.xyz", "18comic.org"]
            )
            if not isinstance(domain_list, list):
                logger.warning(f"domain_list不是列表，尝试转换: {domain_list}")
                if isinstance(domain_list, str):
                    domain_list = domain_list.split(",")
                else:
                    domain_list = ["18comic.vip", "jm365.xyz", "18comic.org"]

            # 处理代理设置
            proxy_value = config.get("proxy", "")
            proxy = None
            if proxy_value and isinstance(proxy_value, str) and proxy_value.strip():
                proxy = proxy_value.strip()
                logger.info(f"使用代理: {proxy}")

            # 处理max_threads，确保是整数
            try:
                max_threads = int(config.get("max_threads", 10))
            except (ValueError, TypeError):
                logger.warning(
                    f"max_threads转换为整数失败: {config.get('max_threads')}"
                )
                max_threads = 10

            # 处理debug_mode，确保是布尔值
            debug_mode = bool(config.get("debug_mode", False))

            # 转换AstrBot配置为CosmosConfig实例
            self.config = CosmosConfig(
                domain_list=domain_list,
                proxy=proxy,
                avs_cookie=str(config.get("avs_cookie", "")),
                max_threads=max_threads,
                debug_mode=debug_mode,
                show_cover=bool(config.get("show_cover", True)),  # 添加 show_cover
            )
            logger.info("已加载AstrBot配置")
        else:
            logger.info("没有收到AstrBot配置，尝试从配置文件加载")

            # 检查是否存在旧的配置文件
            old_config_path = os.path.join(
                self.context.get_config().get("data_dir", "data"),
                "config",
                f"{self.plugin_name}_config.json",
            )

            # 如果旧配置文件存在且新配置文件不存在，则进行迁移
            if os.path.exists(old_config_path) and not os.path.exists(
                self.astrbot_config_path
            ):
                try:
                    logger.info(f"发现旧配置文件: {old_config_path}，尝试迁移")
                    # 确保目录存在
                    os.makedirs(
                        os.path.dirname(self.astrbot_config_path), exist_ok=True
                    )
                    # 复制文件内容
                    with open(old_config_path, "r", encoding="utf-8") as src:
                        with open(
                            self.astrbot_config_path, "w", encoding="utf-8"
                        ) as dst:
                            dst.write(src.read())
                    logger.info(f"已迁移旧配置文件到: {self.astrbot_config_path}")
                except Exception as e:
                    logger.error(f"迁移旧配置文件失败: {str(e)}")

            # 尝试从AstrBot配置文件加载
            if os.path.exists(self.astrbot_config_path):
                try:
                    logger.info(
                        f"尝试从AstrBot配置文件加载: {self.astrbot_config_path}"
                    )
                    with open(
                        self.astrbot_config_path, "r", encoding="utf-8-sig"
                    ) as f:  # 使用 utf-8-sig
                        astrbot_config = json.load(f)

                    # 处理domain_list，确保是列表
                    domain_list = astrbot_config.get(
                        "domain_list", ["18comic.vip", "jm365.xyz", "18comic.org"]
                    )
                    if not isinstance(domain_list, list):
                        if isinstance(domain_list, str):
                            domain_list = domain_list.split(",")
                        else:
                            domain_list = ["18comic.vip", "jm365.xyz", "18comic.org"]

                    # 处理代理
                    proxy_value = astrbot_config.get("proxy", "")
                    proxy = None
                    if (
                        proxy_value
                        and isinstance(proxy_value, str)
                        and proxy_value.strip()
                    ):
                        proxy = proxy_value.strip()

                    # 更新配置
                    self.config = CosmosConfig(
                        domain_list=domain_list,
                        proxy=proxy,
                        avs_cookie=str(astrbot_config.get("avs_cookie", "")),
                        max_threads=int(astrbot_config.get("max_threads", 10)),
                        debug_mode=bool(astrbot_config.get("debug_mode", False)),
                        show_cover=bool(
                            astrbot_config.get("show_cover", True)
                        ),  # 添加 show_cover
                    )
                    logger.info("已从AstrBot配置文件加载配置")
                except Exception as e:
                    logger.error(f"从AstrBot配置文件加载失败: {str(e)}")
                    # 使用默认配置
                    self.config = CosmosConfig(
                        domain_list=["18comic.vip", "jm365.xyz", "18comic.org"],
                        proxy=None,
                        avs_cookie="",
                        max_threads=10,
                        debug_mode=False,
                        show_cover=True,  # 添加 show_cover
                    )
                    logger.info("使用默认配置")
            else:
                # 尝试从旧配置文件加载
                if os.path.exists(old_config_path):
                    try:
                        logger.info(f"尝试从旧配置文件加载: {old_config_path}")
                        with open(
                            old_config_path, "r", encoding="utf-8-sig"
                        ) as f:  # 使用 utf-8-sig
                            old_config = json.load(f)

                        # 处理domain_list
                        domain_list = old_config.get(
                            "domain_list", ["18comic.vip", "jm365.xyz", "18comic.org"]
                        )
                        if not isinstance(domain_list, list):
                            if isinstance(domain_list, str):
                                domain_list = domain_list.split(",")
                            else:
                                domain_list = [
                                    "18comic.vip",
                                    "jm365.xyz",
                                    "18comic.org",
                                ]

                        # 处理代理
                        proxy_value = old_config.get("proxy", "")
                        proxy = None
                        if (
                            proxy_value
                            and isinstance(proxy_value, str)
                            and proxy_value.strip()
                        ):
                            proxy = proxy_value.strip()

                        # 更新配置
                        self.config = CosmosConfig(
                            domain_list=domain_list,
                            proxy=proxy,
                            avs_cookie=str(old_config.get("avs_cookie", "")),
                            max_threads=int(old_config.get("max_threads", 10)),
                            debug_mode=bool(old_config.get("debug_mode", False)),
                            show_cover=bool(
                                old_config.get("show_cover", True)
                            ),  # 添加 show_cover
                        )

                        # 在下次使用_update_astrbot_config时会自动迁移
                        logger.info("已从旧配置文件加载配置，将在下次更新时迁移")
                    except Exception as e:
                        logger.error(f"从旧配置文件加载失败: {str(e)}")
                        # 使用默认配置
                        self.config = CosmosConfig(
                            domain_list=["18comic.vip", "jm365.xyz", "18comic.org"],
                            proxy=None,
                            avs_cookie="",
                            max_threads=10,
                            debug_mode=False,
                            show_cover=True,  # 添加 show_cover
                        )
                        logger.info("使用默认配置")
                else:
                    # 使用默认配置
                    self.config = CosmosConfig(
                        domain_list=["18comic.vip", "jm365.xyz", "18comic.org"],
                        proxy=None,
                        avs_cookie="",
                        max_threads=10,
                        debug_mode=False,
                        show_cover=True,  # 添加 show_cover
                    )
                    logger.info("使用默认配置")

        # 初始化客户端工厂和下载器
        self.client_factory = JMClientFactory(self.config, self.resource_manager)
        self.downloader = ComicDownloader(
            self.client_factory, self.resource_manager, self.config
        )

    def _save_debug_info(self, prefix: str, content: str) -> None:
        """保存调试信息到文件"""
        if not self.config.debug_mode:
            return

        try:
            log_path = self.resource_manager.get_log_path(prefix)
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"已保存调试信息到 {log_path}")
        except Exception as e:
            logger.error(f"保存调试信息失败: {str(e)}")

    async def _build_album_message(
        self, client, album, album_id: str, cover_path: str
    ) -> List:
        """创建漫画信息消息"""
        total_pages = self.downloader.get_total_pages(client, album)
        message = (
            f"📖: {album.title}\n"
            f"🆔: {album_id}\n"
            f"🏷️: {', '.join(album.tags[:5])}\n"
            f"📅: {getattr(album, 'pub_date', '未知')}\n"
            f"📃: {total_pages}"
        )

        # 根据配置决定是否发送封面图片
        if self.config.show_cover:
            return [Plain(text=message), Image.fromFileSystem(cover_path)]
        else:
            return [Plain(text=message)]

    @filter.command("jm")
    async def download_comic(self, event: AstrMessageEvent):
        """下载JM漫画并转换为PDF

        用法: /jm [漫画ID]
        """
        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result("请提供漫画ID，例如：/jm 12345")
            return

        comic_id = args[1]

        # 添加输入验证
        if not validate_comic_id(comic_id):
            yield event.plain_result("无效的漫画ID格式，请提供纯数字ID")
            return

        if self.config.debug_mode:
            yield event.plain_result(
                f"开始下载漫画ID: {comic_id}，请稍候...\n当前配置的最大线程数: {self.config.max_threads}"
            )
        else:
            yield event.plain_result(f"开始下载漫画ID: {comic_id}，请稍候...")

        pdf_path = self.resource_manager.get_pdf_path(comic_id)
        abs_pdf_path = os.path.abspath(pdf_path)
        pdf_name = f"{comic_id}.pdf"

        async def send_the_file(file_path, file_name):
            try:
                # 获取文件大小
                file_size = os.path.getsize(file_path) / (1024 * 1024)  # 转换为MB
                if file_size > 90:
                    yield event.plain_result(
                        f"⚠️ 文件大小为 {file_size:.2f}MB，超过建议的90MB，可能无法发送"
                    )

                if self.config.debug_mode:
                    yield event.plain_result(
                        f"调试信息：尝试发送文件路径 {file_path}，名称 {file_name}，大小 {file_size:.2f}MB"
                    )

                # 检查平台是否为 aiocqhttp
                if event.get_platform_name() == "aiocqhttp" and event.get_group_id():
                    logger.info(
                        "检测到aiocqhttp平台和群组ID，尝试直接调用API发送群文件"
                    )
                    from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
                        AiocqhttpMessageEvent,
                    )

                    if isinstance(event, AiocqhttpMessageEvent):
                        client = event.bot
                        group_id = event.get_group_id()
                        try:
                            # 设置更长的超时时间用于大文件上传
                            import asyncio

                            # 根据文件大小计算超时时间：基础60秒 + 每10MB额外30秒
                            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                            timeout_seconds = 60 + int(file_size_mb / 10) * 30
                            logger.info(
                                f"上传 {file_size_mb:.1f}MB 文件，设置超时时间: {timeout_seconds}秒"
                            )

                            # 1. 上传群文件（带超时控制）
                            upload_result = await asyncio.wait_for(
                                client.upload_group_file(
                                    group_id=group_id, file=file_path, name=file_name
                                ),
                                timeout=timeout_seconds,
                            )
                            logger.info(
                                f"aiocqhttp upload_group_file result: {upload_result}"
                            )
                            logger.info(
                                f"已调用 aiocqhttp upload_group_file API 上传文件 {file_name} 到群组 {group_id}"
                            )

                        except asyncio.TimeoutError:
                            logger.error(
                                f"上传文件超时（{timeout_seconds}秒），文件大小: {file_size_mb:.1f}MB"
                            )
                            yield event.plain_result(
                                f"文件上传超时，文件过大({file_size_mb:.1f}MB)，正在使用备用方式发送..."
                            )
                            # API调用超时，尝试回退到标准方法
                            logger.info("API调用超时，回退到标准 File 组件发送方式")
                            from astrbot.api.message_components import File

                            yield event.chain_result(
                                [File(name=file_name, file=file_path)]
                            )
                        except Exception as api_e:
                            error_type = type(api_e).__name__
                            logger.error(
                                f"调用 aiocqhttp API 发送文件失败({error_type}): {api_e}"
                            )
                            logger.error(traceback.format_exc())
                            yield event.plain_result(
                                f"通过API发送文件失败({error_type})，正在使用备用方式..."
                            )
                            # API调用失败，尝试回退到标准方法
                            logger.info("API调用失败，回退到标准 File 组件发送方式")
                            from astrbot.api.message_components import File

                            yield event.chain_result(
                                [File(name=file_name, file=file_path)]
                            )
                    else:
                        logger.warning(
                            "事件类型不是 AiocqhttpMessageEvent，无法调用特定API，回退到标准发送"
                        )
                        from astrbot.api.message_components import File

                        yield event.chain_result([File(name=file_name, file=file_path)])
                else:
                    # 非aiocqhttp平台或私聊，使用标准方法
                    logger.info("非aiocqhttp平台或私聊，使用标准 File 组件发送方式")
                    from astrbot.api.message_components import File

                    yield event.chain_result([File(name=file_name, file=file_path)])

            except Exception as e:
                error_msg = str(e)
                logger.error(f"发送文件失败: {error_msg}")
                self._save_debug_info(
                    f"send_pdf_error_{comic_id}", traceback.format_exc()
                )
                if "rich media transfer failed" in error_msg:
                    yield event.plain_result(
                        f"QQ富媒体传输失败，文件可能过大或格式不受支持。文件路径: {file_path}"
                    )
                    yield event.plain_result(
                        f"您可以手动从以下路径获取文件: {file_path}"
                    )
                else:
                    yield event.plain_result(f"发送文件失败: {error_msg}")

        # ---- 函数主体 ----
        # 检查是否已经下载过
        if os.path.exists(abs_pdf_path):
            yield event.plain_result("漫画已存在，直接发送...")
            async for result in send_the_file(abs_pdf_path, pdf_name):
                yield result
            return

        # 下载漫画
        # ... (省略下载逻辑) ...
        success, msg = await self.downloader.download_comic(comic_id)
        # ... (省略下载后处理和日志) ...

        if not success:
            yield event.plain_result(f"下载漫画失败: {msg}")
            return

        # 检查PDF是否生成成功
        if not os.path.exists(abs_pdf_path):
            # ... (省略查找和重命名PDF的逻辑) ...
            pdf_files = glob.glob(f"{self.resource_manager.pdfs_dir}/*.pdf")
            if not pdf_files:
                yield event.plain_result("PDF生成失败")
                return
            latest_pdf = max(pdf_files, key=os.path.getmtime)
            try:
                os.rename(latest_pdf, abs_pdf_path)
                logger.info(f"PDF文件已重命名为: {abs_pdf_path}")
            except Exception as rename_e:
                logger.error(f"重命名PDF文件失败: {rename_e}")
                yield event.plain_result(f"PDF生成后重命名失败: {rename_e}")
                return

        # 发送PDF
        yield event.plain_result(f" {comic_id} 下载完成，准备发送...")  # 添加发送提示
        async for result in send_the_file(abs_pdf_path, pdf_name):
            yield result

    @filter.command("jminfo")
    async def get_comic_info(self, event: AstrMessageEvent):
        """获取JM漫画信息

        用法: /jminfo [漫画ID]
        """
        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result("请提供漫画ID，例如：/jminfo 12345")
            return

        comic_id = args[1]

        # 添加输入验证
        if not validate_comic_id(comic_id):
            yield event.plain_result("无效的漫画ID格式，请提供纯数字ID")
            return

        client = self.client_factory.create_client()

        try:
            try:
                album = client.get_album_detail(comic_id)
            except Exception as e:
                error_msg = handle_download_error(e, "获取漫画信息")
                if "网站结构可能已更改" in error_msg:
                    # 尝试手动解析
                    try:
                        html_content = client._postman.get_html(
                            f"https://{self.config.domain_list[0]}/album/{comic_id}"
                        )
                        self._save_debug_info(f"info_html_{comic_id}", html_content)
                        title = extract_title_from_html(html_content)
                        yield event.plain_result(f"{error_msg}\n但找到了标题: {title}")
                    except Exception:
                        yield event.plain_result(error_msg)
                    return
                else:
                    yield event.plain_result(error_msg)
                    return

            cover_path = self.resource_manager.get_cover_path(comic_id)

            if not os.path.exists(cover_path):
                success, result = await self.downloader.download_cover(comic_id)
                if not success:
                    yield event.plain_result(f"{album.title}\n封面下载失败: {result}")
                    return
                cover_path = result

            yield event.chain_result(
                await self._build_album_message(client, album, comic_id, cover_path)
            )
        except Exception as e:
            error_msg = str(e)
            logger.error(f"获取漫画信息失败: {error_msg}")
            self._save_debug_info(f"info_error_{comic_id}", traceback.format_exc())
            yield event.plain_result(f"获取漫画信息失败: {error_msg}")

    @filter.command("jmrecommend")
    async def recommend_comic(self, event: AstrMessageEvent):
        """随机推荐JM漫画

        用法: /jmrecommend
        """
        client = self.client_factory.create_client()
        yield event.plain_result("正在获取推荐漫画，请稍候...")

        try:
            # 尝试获取月榜，如果失败则使用备选方案
            ranking = None
            try:
                ranking = client.month_ranking(1)
            except Exception as e:
                error_msg = str(e)
                logger.error(f"获取月榜失败: {error_msg}")

                # 尝试使用不同的域名
                for domain in self.config.domain_list[1:]:
                    try:
                        logger.info(f"尝试使用域名 {domain} 获取排行榜")
                        temp_client = self.client_factory.create_client_with_domain(
                            domain
                        )
                        ranking = temp_client.month_ranking(1)
                        if ranking:
                            logger.info(f"域名 {domain} 获取排行榜成功")
                            break
                    except Exception as domain_e:
                        logger.error(f"尝试域名 {domain} 失败: {str(domain_e)}")

            # 如果无法获取排行榜，使用内置的热门ID
            if not ranking:
                popular_ids = [
                    "376448",
                    "358333",
                    "375872",
                    "377315",
                    "376870",
                    "375784",
                    "374463",
                    "374160",
                    "373768",
                    "373548",
                ]
                album_id = random.choice(popular_ids)
                yield event.plain_result(
                    f"获取排行榜失败，随机推荐一部热门漫画(ID: {album_id})..."
                )
            else:
                # 从排行榜中随机选择
                ranking_list = list(ranking.iter_id_title())
                album_id, title = random.choice(ranking_list)
                yield event.plain_result(f"从排行榜中随机推荐: [{album_id}] {title}")

            # 获取漫画详情
            try:
                album = client.get_album_detail(album_id)
                logger.info(f"获取到漫画详情: {album_id}, 标题: {album.title}")
            except Exception as e:
                error_msg = str(e)
                logger.error(f"获取漫画详情失败: {error_msg}")
                yield event.plain_result(
                    f"获取漫画详情失败: {error_msg}\n请尝试使用 #jmconfig clearcache 清理封面缓存后再试"
                )
                return

            # 强制重新下载封面
            yield event.plain_result(f"正在下载封面，ID: {album_id}...")
            success, result = await self.downloader.download_cover(album_id)

            if success:
                cover_path = result
                logger.info(f"封面下载成功: {cover_path}")
            else:
                logger.error(f"封面下载失败: {result}")
                yield event.plain_result(
                    f"封面下载失败: {result}\n尝试继续显示漫画信息"
                )
                cover_path = self.resource_manager.get_cover_path(album_id)

            # 显示漫画信息
            yield event.chain_result(
                await self._build_album_message(client, album, album_id, cover_path)
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"推荐漫画失败: {error_msg}")
            self._save_debug_info("recommend_error", traceback.format_exc())
            yield event.plain_result(
                f"推荐漫画失败: {error_msg}\n请尝试使用 #jmconfig clearcache 清理封面缓存后再试"
            )

    @filter.command("jmsearch")
    async def search_comic(self, event: AstrMessageEvent):
        """搜索JM漫画

        用法: /jmsearch [关键词] [序号]
        """
        parts = event.message_str.strip().split()
        if len(parts) < 3:
            yield event.plain_result("格式: /jmsearch [关键词] [序号]")
            return

        *keywords, order = parts[1:]
        try:
            order = int(order)
            if order < 1:
                yield event.plain_result("序号必须≥1")
                return
        except Exception:
            yield event.plain_result("序号必须是数字")
            return

        client = self.client_factory.create_client()
        search_query = " ".join(f"+{k}" for k in keywords)

        yield event.plain_result(
            f"正在搜索: {' '.join(keywords)}，请求序号: {order}..."
        )

        results = []
        try:
            # 查询多页直到找到足够的结果或者达到最大页数
            max_pages = 5  # 最多查询5页
            for page in range(1, max_pages + 1):
                try:
                    logger.info(
                        f"搜索第{page}页，当前结果数: {len(results)}，目标序号: {order}"
                    )
                    search_result = client.search_site(search_query, page)
                    page_results = list(search_result.iter_id_title())

                    if self.config.debug_mode:
                        result_info = "\n".join(
                            [
                                f"{i + 1}. [{id}] {title}"
                                for i, (id, title) in enumerate(page_results)
                            ]
                        )
                        logger.info(f"第{page}页搜索结果:\n{result_info}")

                    results.extend(page_results)
                    if len(results) >= order:
                        logger.info(f"已找到足够的结果: {len(results)} >= {order}")
                        break
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"搜索第{page}页失败: {error_msg}")
                    if "文本没有匹配上字段" in error_msg:
                        yield event.plain_result(
                            "搜索失败: 网站结构可能已更改，请更新jmcomic库"
                        )
                        return
                    elif page == 1:  # 如果第一页就失败，则返回错误
                        yield event.plain_result(f"搜索失败: {error_msg}")
                        return
                    else:  # 如果不是第一页失败，可以继续用之前的结果
                        break

            if len(results) == 0:
                yield event.plain_result("未找到任何结果")
                return

            if len(results) < order:
                # 找到了一些结果，但不够满足序号要求
                result_list = "\n".join(
                    [f"{i + 1}. [{id}] {title}" for i, title in enumerate(results)]
                )
                yield event.plain_result(
                    f"仅找到{len(results)}条结果，无法显示第{order}条:\n{result_list}"
                )
                return

            # 获取指定序号的漫画ID和标题
            album_id, title = results[order - 1]
            logger.info(f"请求序号 {order}，展示漫画: [{album_id}] {title}")

            try:
                album = client.get_album_detail(album_id)
            except Exception as e:
                error_msg = str(e)
                logger.error(f"获取漫画详情失败: {error_msg}")
                if "文本没有匹配上字段" in error_msg:
                    yield event.plain_result(
                        f"获取漫画详情失败: 网站结构可能已更改，但搜索结果ID是: {album_id}，标题: {title}"
                    )
                    return
                else:
                    yield event.plain_result(f"获取漫画详情失败: {error_msg}")
                    return

            # 始终重新下载封面以确保正确
            yield event.plain_result(
                f"搜索结果第{order}条: [{album_id}] {album.title}\n正在下载封面..."
            )
            success, cover_path = await self.downloader.download_cover(album_id)
            if not success:
                yield event.plain_result(
                    f"封面下载失败: {cover_path}\n但搜索结果ID是: {album_id}，标题: {album.title}"
                )
                # 尝试使用预期的封面路径继续
                cover_path = self.resource_manager.get_cover_path(album_id)

            # 显示漫画信息
            yield event.chain_result(
                await self._build_album_message(client, album, album_id, cover_path)
            )
        except Exception as e:
            error_msg = str(e)
            logger.error(f"搜索漫画失败: {error_msg}")
            self._save_debug_info("search_error", traceback.format_exc())
            yield event.plain_result(f"搜索漫画失败: {error_msg}")

    @filter.command("jmauthor")
    async def search_author(self, event: AstrMessageEvent):
        """搜索JM漫画作者作品

        用法: /jmauthor [作者名] [序号]
        """
        parts = event.message_str.strip().split()
        if len(parts) < 3:
            yield event.plain_result("格式: /jmauthor [作者名] [序号]")
            return

        *author_parts, order = parts[1:]
        try:
            order = int(order)
            if order < 1:
                yield event.plain_result("序号必须≥1")
                return
        except Exception:
            yield event.plain_result("序号必须是数字")
            return

        client = self.client_factory.create_client()
        author_name = " ".join(author_parts)

        # 直接使用有效的搜索格式
        search_query = author_name
        all_results = []

        try:
            logger.info(f"搜索作者: '{author_name}'")
            first_page = client.search_site(
                search_query=search_query,
                page=1,
                order_by=JmMagicConstants.ORDER_BY_LATEST,
            )
            total_count = first_page.total

            if total_count == 0:
                yield event.plain_result(
                    f"未找到作者 {author_name} 的作品，请检查作者名是否正确"
                )
                return

            logger.info(f"搜索成功，找到 {total_count} 部作品")
            page_size = len(first_page.content)
            all_results.extend(list(first_page.iter_id_title()))

            # 获取足够的结果来显示前N部作品
            target_count = min(order, total_count)  # 最多获取用户要求的数量

            # 计算需要请求的总页数
            if total_count > 0 and page_size > 0:
                total_page = (total_count + page_size - 1) // page_size
                # 请求剩余页，直到获取到足够的作品
                for page in range(2, total_page + 1):
                    try:
                        page_result = client.search_site(
                            search_query=search_query,
                            page=page,
                            order_by=JmMagicConstants.ORDER_BY_LATEST,
                        )
                        all_results.extend(list(page_result.iter_id_title()))
                    except Exception as e:
                        logger.error(f"获取第{page}页失败: {str(e)}")

                    # 提前终止条件：已获取足够的作品
                    if len(all_results) >= target_count:
                        break

            # 检查是否获取到足够的作品
            available_count = min(len(all_results), target_count)
            if available_count == 0:
                yield event.plain_result(
                    f"作者 {author_name} 共有 {total_count} 部作品，但无法获取作品列表"
                )
                return

            # 构建作品列表信息
            message_parts = [f"🎨 作者 {author_name} 共有 {total_count} 部作品"]
            message_parts.append(f"📋 显示前 {available_count} 部作品:")

            for i in range(available_count):
                album_id, title = all_results[i]
                message_parts.append(f"{i + 1}. 🆔{album_id}: {title}")

            # 如果只要求1部作品，还是下载封面
            if order == 1:
                album_id, _ = all_results[0]
                try:
                    album = client.get_album_detail(album_id)
                    cover_path = self.resource_manager.get_cover_path(album_id)
                    if not os.path.exists(cover_path):
                        success, result = await self.downloader.download_cover(album_id)
                        if not success:
                            yield event.plain_result(f"⚠️ 封面下载失败: {result}")
                            return
                        cover_path = result

                    detailed_message = (
                        f"🎨 作者 {author_name} 共有 {total_count} 部作品\n"
                        f"📖: {album.title}\n"
                        f"🆔: {album_id}\n"
                        f"🏷️: {', '.join(album.tags[:3])}\n"
                        f"📅: {getattr(album, 'pub_date', '未知')}\n"
                        f"📃: {self.downloader.get_total_pages(client, album)}"
                    )

                    yield event.chain_result(
                        [Plain(text=detailed_message), Image.fromFileSystem(cover_path)]
                    )
                    return
                except Exception as e:
                    logger.error(f"获取详细信息失败: {str(e)}")
                    # 如果获取详细信息失败，继续显示列表

            # 显示作品列表
            yield event.plain_result("\n".join(message_parts))
        except Exception as e:
            error_msg = str(e)
            logger.error(f"搜索作者失败: {error_msg}")
            self._save_debug_info("author_error", traceback.format_exc())
            yield event.plain_result(f"搜索作者失败: {error_msg}")

    @filter.command("jmconfig")
    async def config_plugin(self, event: AstrMessageEvent):
        """配置JM漫画下载插件

        用法:
        /jmconfig proxy [代理URL] - 设置代理URL，例如：http://127.0.0.1:7890
        /jmconfig noproxy - 清除代理设置
        /jmconfig cookie [AVS Cookie] - 设置登录Cookie
        /jmconfig threads [数量] - 设置最大下载线程数
        /jmconfig domain [域名] - 添加JM漫画域名
        /jmconfig debug [on/off] - 开启/关闭调试模式
        /jmconfig cover [on/off] - 控制是否显示封面图片
        /jmconfig info - 显示当前配置信息
        /jmconfig reload - 重新加载配置文件
        /jmconfig clearcache - 清理封面缓存
        """
        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result(
                "用法:\n/jmconfig proxy [代理URL] - 设置代理URL\n/jmconfig noproxy - 清除代理设置\n/jmconfig cookie [AVS Cookie] - 设置登录Cookie\n/jmconfig threads [数量] - 设置最大下载线程数\n/jmconfig domain [域名] - 添加JM漫画域名\n/jmconfig debug [on/off] - 开启/关闭调试模式\n/jmconfig cover [on/off] - 控制是否显示封面图片\n/jmconfig info - 显示当前配置信息\n/jmconfig reload - 重新加载配置文件\n/jmconfig clearcache - 清理封面缓存"
            )
            return

        action = args[1].lower()

        if action == "clearcache":
            # 清理封面缓存
            count = self.resource_manager.clear_cover_cache()
            yield event.plain_result(f"封面缓存清理完成，共删除 {count} 个文件")
            return

        if action == "info":
            # 显示当前配置信息
            domain_list_str = ", ".join(self.config.domain_list)
            proxy_str = self.config.proxy if self.config.proxy else "未设置"
            cookie_str = "已设置" if self.config.avs_cookie else "未设置"
            threads_str = str(self.config.max_threads)
            debug_str = "开启" if self.config.debug_mode else "关闭"
            cover_str = "显示" if self.config.show_cover else "不显示"

            info_message = (
                f"当前配置信息:\n"
                f"域名列表: {domain_list_str}\n"
                f"代理: {proxy_str}\n"
                f"Cookie: {cookie_str}\n"
                f"最大线程数: {threads_str}\n"
                f"调试模式: {debug_str}\n"
                f"显示封面: {cover_str}"
            )

            yield event.plain_result(info_message)
            return

        elif action == "reload":
            # 重新加载配置
            try:
                # 尝试从AstrBot配置加载
                if os.path.exists(self.astrbot_config_path):
                    try:
                        with open(
                            self.astrbot_config_path, "r", encoding="utf-8-sig"
                        ) as f:  # 使用 utf-8-sig
                            astrbot_config = json.load(f)

                        # 处理domain_list
                        domain_list = astrbot_config.get(
                            "domain_list", ["18comic.vip", "jm365.xyz", "18comic.org"]
                        )
                        if not isinstance(domain_list, list):
                            if isinstance(domain_list, str):
                                domain_list = domain_list.split(",")
                            else:
                                domain_list = [
                                    "18comic.vip",
                                    "jm365.xyz",
                                    "18comic.org",
                                ]

                        # 处理代理
                        proxy_value = astrbot_config.get("proxy", "")
                        proxy = None
                        if (
                            proxy_value
                            and isinstance(proxy_value, str)
                            and proxy_value.strip()
                        ):
                            proxy = proxy_value.strip()

                        # 更新配置
                        self.config = CosmosConfig(
                            domain_list=domain_list,
                            proxy=proxy,
                            avs_cookie=str(astrbot_config.get("avs_cookie", "")),
                            max_threads=int(astrbot_config.get("max_threads", 10)),
                            debug_mode=bool(astrbot_config.get("debug_mode", False)),
                            show_cover=bool(
                                astrbot_config.get("show_cover", True)
                            ),  # 添加 show_cover
                        )

                        # 更新客户端工厂
                        self.client_factory.update_option()

                        yield event.plain_result("已重新加载配置")
                        return
                    except Exception as e:
                        logger.error(f"从AstrBot配置加载失败: {str(e)}")
                        yield event.plain_result(f"重新加载配置失败: {str(e)}")
                        return

                yield event.plain_result("未找到配置文件，请先在管理面板中设置配置")
            except Exception as e:
                logger.error(f"重新加载配置失败: {str(e)}", exc_info=True)
                yield event.plain_result(f"重新加载配置失败: {str(e)}")
            return

        elif action == "proxy" and len(args) >= 3:
            proxy_url = args[2]
            self.config.proxy = proxy_url
            # 更新AstrBot配置
            if self._update_astrbot_config("proxy", proxy_url):
                # 更新客户端工厂选项
                self.client_factory.update_option()
                yield event.plain_result(f"已设置代理URL为: {proxy_url}")
            else:
                yield event.plain_result("保存配置失败，请检查权限")
        elif action == "noproxy":
            self.config.proxy = None
            if self._update_astrbot_config("proxy", ""):
                # 更新客户端工厂选项
                self.client_factory.update_option()
                yield event.plain_result("已清除代理设置")
            else:
                yield event.plain_result("保存配置失败，请检查权限")
        elif action == "cookie" and len(args) >= 3:
            cookie = args[2]
            self.config.avs_cookie = cookie
            if self._update_astrbot_config("avs_cookie", cookie):
                # 更新客户端工厂选项
                self.client_factory.update_option()
                yield event.plain_result("已设置登录Cookie")
            else:
                yield event.plain_result("保存配置失败，请检查权限")
        elif action == "threads" and len(args) >= 3:
            try:
                threads = int(args[2])
                if threads < 1:
                    yield event.plain_result("线程数必须≥1")
                    return
                self.config.max_threads = threads
                if self._update_astrbot_config("max_threads", threads):
                    # 更新客户端工厂选项
                    self.client_factory.update_option()
                    yield event.plain_result(f"已设置最大下载线程数为: {threads}")
                else:
                    yield event.plain_result("保存配置失败，请检查权限")
            except Exception:
                yield event.plain_result("线程数必须是整数")
        elif action == "domain" and len(args) >= 3:
            domain = args[2]

            # 添加域名格式验证
            if not validate_domain(domain):
                yield event.plain_result("无效的域名格式")
                return

            if domain not in self.config.domain_list:
                self.config.domain_list.append(domain)
                if self._update_astrbot_config("domain_list", self.config.domain_list):
                    # 更新客户端工厂选项
                    self.client_factory.update_option()
                    logger.info(f"已添加域名到配置: {domain}")
                    yield event.plain_result(f"已添加域名: {domain}")
                else:
                    yield event.plain_result("保存配置失败，请检查权限")
            else:
                yield event.plain_result(f"域名已存在: {domain}")

        elif action == "debug" and len(args) >= 3:
            debug_mode = args[2].lower()
            if debug_mode == "on":
                self.config.debug_mode = True
                # 更新AstrBot配置
                if self._update_astrbot_config("debug_mode", True):
                    # 更新客户端工厂选项
                    self.client_factory.update_option()
                    yield event.plain_result("已开启调试模式")
                else:
                    yield event.plain_result("保存配置失败，请检查权限")
            elif debug_mode == "off":
                self.config.debug_mode = False
                # 更新AstrBot配置
                if self._update_astrbot_config("debug_mode", False):
                    # 更新客户端工厂选项
                    self.client_factory.update_option()
                    yield event.plain_result("已关闭调试模式")
                else:
                    yield event.plain_result("保存配置失败，请检查权限")
            else:
                yield event.plain_result("参数错误，请使用 on 或 off")
        elif action == "cover" and len(args) >= 3:
            cover_mode = args[2].lower()
            if cover_mode == "on":
                self.config.show_cover = True
                # 更新AstrBot配置
                if self._update_astrbot_config("show_cover", True):
                    yield event.plain_result("已开启封面图片显示")
                else:
                    yield event.plain_result("保存配置失败，请检查权限")
            elif cover_mode == "off":
                self.config.show_cover = False
                # 更新AstrBot配置
                if self._update_astrbot_config("show_cover", False):
                    yield event.plain_result("已关闭封面图片显示")
                else:
                    yield event.plain_result("保存配置失败，请检查权限")
            else:
                yield event.plain_result("参数错误，请使用 on 或 off")
        else:
            yield event.plain_result("不支持的配置项或参数不足")

    def _update_astrbot_config(self, key: str, value) -> bool:
        """更新AstrBot配置文件"""
        try:
            config_dir = os.path.join(
                self.context.get_config().get("data_dir", "data"), "config"
            )
            config_path = os.path.join(
                config_dir, f"astrbot_plugin_{self.plugin_name}_config.json"
            )

            # 确保目录存在
            os.makedirs(config_dir, exist_ok=True)

            # 读取现有配置或创建新配置
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8-sig") as f:
                    config = json.load(f)
            else:
                config = {}

            # 更新配置
            config[key] = value

            # 保存配置
            with open(config_path, "w", encoding="utf-8-sig") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)

            logger.info(f"已更新AstrBot配置: {key}={value}")

            # 如果存在旧的错误配置文件，尝试迁移内容并删除
            old_config_path = os.path.join(
                config_dir, f"{self.plugin_name}_config.json"
            )
            if os.path.exists(old_config_path) and old_config_path != config_path:
                try:
                    # 读取旧配置
                    with open(old_config_path, "r", encoding="utf-8-sig") as f:
                        old_config = json.load(f)

                    # 合并到新配置文件中
                    for k, v in old_config.items():
                        if k not in config:
                            config[k] = v

                    # 保存合并后的配置
                    with open(config_path, "w", encoding="utf-8-sig") as f:
                        json.dump(config, f, ensure_ascii=False, indent=2)

                    # 删除旧配置文件
                    os.remove(old_config_path)
                    logger.info(f"已迁移旧配置文件 {old_config_path} 到 {config_path}")
                except Exception as e:
                    logger.error(f"迁移旧配置文件失败: {str(e)}")

            return True
        except Exception as e:
            logger.error(f"更新AstrBot配置失败: {str(e)}", exc_info=True)
            return False

    @filter.command("jmimg")
    async def download_comic_as_images(self, event: AstrMessageEvent):
        """下载JM漫画前几页作为预览

        用法: /jmimg [漫画ID] [可选:页数，默认3页]
        """
        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result("请提供漫画ID，例如：/jmimg 12345")
            return

        comic_id = args[1]

        # 添加输入验证
        if not validate_comic_id(comic_id):
            yield event.plain_result("无效的漫画ID格式，请提供纯数字ID")
            return

        max_pages = 3  # 默认预览前3页

        if len(args) > 2:
            try:
                max_pages = int(args[2])
                if max_pages < 1:
                    max_pages = 1
                elif max_pages > 10:  # 限制最多10页，避免消息过大
                    max_pages = 10
            except Exception:
                pass

        yield event.plain_result(
            f"开始预览下载漫画ID: {comic_id}的前{max_pages}页，请稍候..."
        )

        try:
            # 获取JM客户端
            client = self.client_factory.create_client()
            if not client:
                yield event.plain_result("无法连接到JM网站，请检查网络连接")
                return

            # 使用预览下载功能
            success, message, image_paths = self.downloader.preview_download_comic(
                client, comic_id, max_pages
            )

            if not success:
                yield event.plain_result(f"预览下载失败: {message}")
                return

            if not image_paths:
                yield event.plain_result("预览下载成功但未获取到图片")
                return

            # 发送图片
            logger.info(f"准备发送 {len(image_paths)} 张预览图片")

            for i, image_path in enumerate(image_paths, 1):
                try:
                    if os.path.exists(image_path):
                        # 检查图片大小
                        file_size = os.path.getsize(image_path) / (1024 * 1024)  # MB

                        if file_size > 20:  # 大于20MB
                            logger.warning(
                                f"图片 {image_path} 太大 ({file_size:.1f}MB)，跳过发送"
                            )
                            yield event.plain_result(
                                f"第{i}页图片过大({file_size:.1f}MB)，跳过发送"
                            )
                            continue

                        # 添加延迟避免发送过快
                        if i > 1:
                            await asyncio.sleep(1)

                        yield event.image_result(image_path)
                        logger.info(f"已发送第{i}页预览图片")
                    else:
                        logger.warning(f"图片文件不存在: {image_path}")

                except Exception as e:
                    logger.error(f"发送第{i}页图片失败: {str(e)}")
                    yield event.plain_result(f"发送第{i}页图片失败")

            yield event.plain_result(
                f"✅ 预览完成！已发送 {len(image_paths)} 页\n💡 如需完整漫画，请使用 /jm {comic_id}"
            )

            # 清理预览文件（可选，节省空间）
            try:
                preview_dir = os.path.dirname(image_paths[0]) if image_paths else None
                if preview_dir and os.path.exists(preview_dir):
                    import shutil

                    shutil.rmtree(preview_dir)
                    logger.info(f"已清理预览文件夹: {preview_dir}")
            except Exception as e:
                logger.warning(f"清理预览文件失败: {str(e)}")

        except Exception as e:
            logger.error(f"预览下载过程中出错: {str(e)}", exc_info=True)
            yield event.plain_result(f"预览下载失败: {str(e)}")

    @filter.command("jmpdf")
    async def check_pdf_info(self, event: AstrMessageEvent):
        """查看PDF文件信息

        用法: /jmpdf [漫画ID]
        """
        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result("请提供漫画ID，例如：/jmpdf 12345")
            return

        comic_id = args[1]

        # 添加输入验证
        if not validate_comic_id(comic_id):
            yield event.plain_result("无效的漫画ID格式，请提供纯数字ID")
            return

        pdf_path = self.resource_manager.get_pdf_path(comic_id)

        if not os.path.exists(pdf_path):
            yield event.plain_result(f"PDF文件不存在: {pdf_path}")
            return

        # 获取文件信息
        try:
            file_size = os.path.getsize(pdf_path) / (1024 * 1024)  # MB
            creation_time = datetime.fromtimestamp(os.path.getctime(pdf_path)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            modify_time = datetime.fromtimestamp(os.path.getmtime(pdf_path)).strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            # 获取漫画信息
            try:
                client = self.client_factory.create_client()
                album = client.get_album_detail(comic_id)
                title = album.title
            except Exception:
                title = f"漫画_{comic_id}"

            # 文件大小等级评估
            size_level = "正常"
            size_note = ""
            if file_size > 100:
                size_level = "⚠️ 超过QQ文件上限"
                size_note = "无法通过QQ发送，建议使用 /jmimg 命令查看前几页"
            elif file_size > 90:
                size_level = "⚠️ 接近QQ文件上限"
                size_note = "发送可能失败，建议使用 /jmimg 命令"
            elif file_size > 50:
                size_level = "⚠️ 较大"
                size_note = "发送可能较慢"

            # 获取原始图片目录信息
            img_folder = self.resource_manager.get_comic_folder(comic_id)
            total_images = 0
            image_folders = []

            if os.path.exists(img_folder):
                # 检查主目录下是否直接有图片
                direct_images = [
                    f
                    for f in os.listdir(img_folder)
                    if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
                    and os.path.isfile(os.path.join(img_folder, f))
                ]

                if direct_images:
                    total_images = len(direct_images)
                    image_folders.append(f"主目录({total_images}张)")
                else:
                    # 检查所有子目录中的图片
                    for photo_folder in os.listdir(img_folder):
                        photo_path = os.path.join(img_folder, photo_folder)
                        if os.path.isdir(photo_path):
                            image_count = len(
                                [
                                    f
                                    for f in os.listdir(photo_path)
                                    if f.lower().endswith(
                                        (".jpg", ".jpeg", ".png", ".webp")
                                    )
                                    and os.path.isfile(os.path.join(photo_path, f))
                                ]
                            )
                            if image_count > 0:
                                total_images += image_count
                                image_folders.append(f"{photo_folder}({image_count}张)")

            info_text = (
                f"📖 {title}\n"
                f"🆔 {comic_id}\n"
                f"📁 文件大小: {file_size:.2f} MB ({size_level})\n"
                f"📅 创建时间: {creation_time}\n"
                f"🔄 修改时间: {modify_time}\n"
                f"🖼️ 总图片数: {total_images}张\n"
                f"📚 章节: {', '.join(image_folders[:5])}"
            )

            if size_note:
                info_text += f"\n📝 注意: {size_note}"

            if not os.path.exists(img_folder):
                info_text += "\n⚠️ 原始图片目录不存在，无法使用 /jmimg 命令"
            elif total_images == 0:
                info_text += (
                    "\n⚠️ 未找到图片文件，但目录存在。可能需要重新下载或使用其他命令"
                )

            yield event.plain_result(info_text)

        except Exception as e:
            error_msg = str(e)
            logger.error(f"获取PDF信息失败: {error_msg}")
            yield event.plain_result(f"获取PDF信息失败: {error_msg}")

    @filter.command("jmdomain")
    async def test_domains(self, event: AstrMessageEvent):
        """测试并获取可用的禁漫域名

        用法: /jmdomain [选项]
        选项: test - 测试所有域名并显示结果
              update - 测试并自动更新可用域名
              list - 显示当前配置的域名
        """
        args = event.message_str.strip().split()

        # 如果没有提供二级指令，显示帮助信息
        if len(args) < 2:
            help_text = (
                "📋 禁漫域名工具用法:\n\n"
                "/jmdomain list - 显示当前配置的域名\n"
                "/jmdomain test - 测试所有可获取的域名并显示结果\n"
                "/jmdomain update - 测试并自动更新为可用域名\n\n"
                "说明: 测试和更新操作可能需要几分钟时间，请耐心等待"
            )
            yield event.plain_result(help_text)
            return

        option = args[1].lower()

        if option == "list":
            # 显示当前配置的域名
            domains_text = "\n".join(
                [
                    f"- {i + 1}. {domain}"
                    for i, domain in enumerate(self.config.domain_list)
                ]
            )
            yield event.plain_result(f"当前配置的域名列表:\n{domains_text}")
            return
        elif option not in ["test", "update"]:
            yield event.plain_result("无效的选项，可用的选项为: list, test, update")
            return

        yield event.plain_result("开始获取全部禁漫域名，这可能需要一些时间...")

        try:
            # 通过异步方式在后台执行域名获取和测试
            domains = await asyncio.to_thread(self._get_all_domains)

            if not domains:
                yield event.plain_result("未能获取到任何域名，请检查网络连接")
                return

            yield event.plain_result(f"获取到{len(domains)}个域名，开始测试可用性...")

            # 测试所有域名
            domain_status = await asyncio.to_thread(self._test_domains, domains)

            # 找出可用的域名
            available_domains = [
                domain for domain, status in domain_status.items() if status == "ok"
            ]

            # 输出结果
            if option == "test":
                # 按状态分组域名
                ok_domains = []
                failed_domains = []

                for domain, status in domain_status.items():
                    if status == "ok":
                        ok_domains.append(domain)
                    else:
                        failed_domains.append(f"{domain}: {status}")

                result = (
                    f"测试完成，共{len(domains)}个域名，其中{len(ok_domains)}个可用\n\n"
                )
                if len(ok_domains) > 0:
                    result += "✅ 可用域名:\n"
                    for i, domain in enumerate(ok_domains[:10]):  # 只显示前10个可用域名
                        result += f"{i + 1}. {domain}\n"

                    if len(ok_domains) > 10:
                        result += f"...等共{len(ok_domains)}个可用域名\n"
                else:
                    result += "❌ 没有找到可用域名\n"
                    # 添加可能的原因和解决方案
                    if not self.config.proxy:
                        result += "\n可能原因:\n1. 所有域名都被屏蔽\n2. 网络问题\n\n建议配置代理后再试:\n#jmconfig proxy http://127.0.0.1:7890\n(将示例的代理地址换成你自己的)"

                yield event.plain_result(result)

            elif option == "update":
                if not available_domains:
                    result = "未找到可用域名，保持当前配置不变"

                    # 添加可能的原因和解决方案
                    if not self.config.proxy:
                        result += "\n\n可能原因:\n1. 所有域名都被屏蔽\n2. 网络问题\n\n建议配置代理后再试:\n#jmconfig proxy http://127.0.0.1:7890\n(将示例的代理地址换成你自己的)"

                    yield event.plain_result(result)
                    return

                # 更新配置
                old_domains = set(self.config.domain_list)
                new_domains = set(available_domains)

                # 移除不可用的域名
                removed_domains = old_domains.difference(new_domains)

                # 更新配置
                self.config.domain_list = list(available_domains[:5])  # 取前5个可用域名
                if self._update_astrbot_config("domain_list", self.config.domain_list):
                    # 更新客户端工厂选项
                    self.client_factory.update_option()
                    # 强制刷新jmcomic库的全局配置
                    logger.info(
                        f"已更新域名配置，新域名列表: {self.config.domain_list}"
                    )
                    # 重新创建客户端工厂以确保使用新配置
                    self.client_factory = JMClientFactory(
                        self.config, self.resource_manager
                    )
                    self.downloader = ComicDownloader(
                        self.client_factory, self.resource_manager, self.config
                    )

                    result = "域名更新完成！\n\n"
                    result += (
                        f"✅ 已配置以下{len(self.config.domain_list)}个可用域名:\n"
                    )
                    for i, domain in enumerate(self.config.domain_list):
                        result += f"{i + 1}. {domain}\n"

                    if removed_domains:
                        result += f"\n❌ 已移除{len(removed_domains)}个不可用域名"

                    yield event.plain_result(result)
                else:
                    yield event.plain_result("更新域名失败，无法保存配置")

        except Exception as e:
            error_msg = str(e)
            logger.error(f"测试域名失败: {error_msg}")
            self._save_debug_info("domain_test_error", traceback.format_exc())
            result = f"测试域名失败: {error_msg}"

            # 添加可能的原因和解决方案
            if "timeout" in error_msg.lower() or "connect" in error_msg.lower():
                result += "\n\n可能是网络问题，建议配置代理后再试:\n#jmconfig proxy http://127.0.0.1:7890\n(将示例的代理地址换成你自己的)"

            yield event.plain_result(result)

    def _get_all_domains(self):
        """获取所有禁漫域名"""
        from curl_cffi import requests as postman

        template = "https://jmcmomic.github.io/go/{}.html"
        url_ls = [template.format(i) for i in range(300, 309)]
        domain_set = set()

        meta_data = {}
        if self.config.proxy:
            meta_data["proxies"] = {"https": self.config.proxy}

        def fetch_domain(url):
            try:
                text = postman.get(url, allow_redirects=False, **meta_data).text
                for domain in jmcomic.JmcomicText.analyse_jm_pub_html(text):
                    if domain.startswith("jm365.work"):
                        continue
                    domain_set.add(domain)
            except Exception as e:
                logger.error(f"获取域名失败 {url}: {str(e)}")

        jmcomic.multi_thread_launcher(
            iter_objs=url_ls,
            apply_each_obj_func=fetch_domain,
        )
        return domain_set

    def _test_domains(self, domain_set):
        """测试域名是否可用"""
        domain_status_dict = {}

        meta_data = {}
        if self.config.proxy:
            meta_data["proxies"] = {"https": self.config.proxy}

        # 已禁用全局日志，无需再次禁用
        jmcomic.disable_jm_log()

        def test_domain(domain):
            try:
                # 直接使用curl_cffi库来测试域名
                from curl_cffi import requests as postman

                domain_url = f"https://{domain}"
                logger.info(f"正在测试域名: {domain}")

                # 使用postman访问主页
                response = postman.get(domain_url, **meta_data)
                html = response.text

                # 检查返回的HTML是否包含一些禁漫网站特有的关键词
                jm_keywords = ["禁漫", "JM", "18comic", "免費", "同人", "成人", "H漫"]

                valid_domain = False
                for keyword in jm_keywords:
                    if keyword in html:
                        valid_domain = True
                        break

                if not valid_domain:
                    # 也尝试访问另一个页面
                    try:
                        search_url = f"https://{domain}/search/albums"
                        search_response = postman.get(search_url, **meta_data)
                        search_html = search_response.text
                        for keyword in jm_keywords:
                            if keyword in search_html:
                                valid_domain = True
                                break
                    except Exception as se:
                        logger.warning(f"尝试访问搜索页面失败: {str(se)}")

                if not valid_domain:
                    status = "页面内容不正确"
                    logger.warning(f"域名 {domain} 可访问但内容不符合预期")
                else:
                    status = "ok"
                    logger.info(f"域名 {domain} 测试通过")

            except Exception as e:
                err_msg = str(e)
                status = f"访问失败: {err_msg[:50]}"
                logger.error(f"测试域名 {domain} 失败: {err_msg}")

            domain_status_dict[domain] = status

        jmcomic.multi_thread_launcher(
            iter_objs=domain_set,
            apply_each_obj_func=test_domain,
        )

        return domain_status_dict

    @filter.command("jmupdate")
    async def check_update(self, event: AstrMessageEvent):
        """检查JM漫画插件更新

        用法: /jmupdate
        """
        yield event.plain_result(
            "JM-Cosmos插件 v1.0.7\n特性:\n 更换文件发送方式，修复文件消息缺少参数问题\n"
            + "\n".join([f"- {domain}" for domain in self.config.domain_list])
        )

    @filter.command("jmhelp")
    async def show_help(self, event: AstrMessageEvent):
        """显示帮助信息"""
        help_text = (
            "📚 JM-Cosmos插件命令列表：\n"
            "1️⃣ /jm [ID] - 下载漫画为PDF\n"
            "2️⃣ /jmimg [ID] [页数] - 发送漫画前几页图片\n"
            "3️⃣ /jminfo [ID] - 查看漫画信息\n"
            "4️⃣ /jmpdf [ID] - 检查PDF文件信息\n"
            "5️⃣ /jmauthor [作者] [序号] - 搜索作者作品\n"
            "6️⃣ /jmsearch [关键词] [序号] - 搜索漫画\n"
            "7️⃣ /jmrecommend - 随机推荐漫画\n"
            "8️⃣ /jmconfig - 配置插件\n"
            "9️⃣ /jmdomain - 测试并更新可用域名\n"
            "🔟 /jmupdate - 检查更新\n"
            "1️⃣1️⃣ /jmstatus - 查看插件状态\n"
            "1️⃣2️⃣ /jmcleanup - 清理过期文件\n"
            "1️⃣3️⃣ /jmfolder [ID] - 调试文件夹匹配\n"
            "1️⃣4️⃣ /jmhelp - 查看帮助\n"
            "📌 说明：\n"
            "· [序号]表示结果中的第几个，从1开始\n"
            "· 搜索多个关键词时用空格分隔\n"
            "· 作者搜索按时间倒序排列\n"
            "· 如果PDF发送失败，可使用/jmimg命令获取图片\n"
            "· 如果遇到网站结构更新导致失败，请通过jmconfig或jmdomain添加新域名\n"
            "· 可通过配置文件的show_cover选项控制是否显示封面图片\n"
            "· 使用/jmstatus查看存储使用情况，/jmcleanup清理过期文件\n"
        )
        yield event.plain_result(help_text)

    @filter.command("jmstatus")
    async def show_status(self, event: AstrMessageEvent):
        """显示插件状态信息"""
        try:
            # 存储信息
            storage_info = self.resource_manager.get_storage_info()

            # 下载状态
            active_downloads = len(self.downloader.downloading_comics)
            active_covers = len(self.downloader.downloading_covers)

            # 配置信息
            config_info = f"域名数: {len(self.config.domain_list)}, 最大线程: {self.config.max_threads}"

            status_text = (
                f"📊 JM-Cosmos 状态报告\n\n"
                f"💾 存储使用: {storage_info['usage_percent']}% "
                f"({storage_info['total_size_mb']}/{storage_info['max_size_mb']} MB)\n"
                f"⬇️ 活跃下载: {active_downloads} 个漫画, {active_covers} 个封面\n"
                f"⚙️ 配置: {config_info}\n"
                f"🌐 代理: {'已配置' if self.config.proxy else '未配置'}\n"
                f"🐛 调试模式: {'开启' if self.config.debug_mode else '关闭'}\n"
                f"🖼️ 封面显示: {'开启' if self.config.show_cover else '关闭'}"
            )

            # 如果存储使用率过高，添加清理建议
            if storage_info["usage_percent"] > 80:
                status_text += "\n\n⚠️ 存储使用率较高，建议执行清理操作"

            yield event.plain_result(status_text)

        except Exception as e:
            logger.error(f"获取状态信息失败: {str(e)}")
            yield event.plain_result(f"获取状态失败: {str(e)}")

    @filter.command("jmcleanup")
    async def cleanup_storage(self, event: AstrMessageEvent):
        """清理过期文件释放存储空间"""
        try:
            yield event.plain_result("开始清理过期文件...")

            # 获取清理前的存储信息
            storage_info_before = self.resource_manager.get_storage_info()

            # 执行清理
            cleaned_count = self.resource_manager.cleanup_old_files()

            # 获取清理后的存储信息
            storage_info_after = self.resource_manager.get_storage_info()

            # 计算释放的空间
            freed_space = (
                storage_info_before["total_size_mb"]
                - storage_info_after["total_size_mb"]
            )

            result_text = (
                f"🧹 清理完成！\n\n"
                f"📁 清理文件数: {cleaned_count} 个\n"
                f"💾 释放空间: {freed_space:.2f} MB\n"
                f"📊 当前使用率: {storage_info_after['usage_percent']}% "
                f"({storage_info_after['total_size_mb']}/{storage_info_after['max_size_mb']} MB)"
            )

            if freed_space > 0:
                result_text += "\n✅ 成功释放存储空间"
            else:
                result_text += "\n💡 没有找到可清理的过期文件"

            yield event.plain_result(result_text)

        except Exception as e:
            logger.error(f"清理存储空间失败: {str(e)}")
            yield event.plain_result(f"清理失败: {str(e)}")

    @filter.command("jmfolder")
    async def debug_folder_matching(self, event: AstrMessageEvent):
        """调试文件夹匹配功能"""
        args = event.message_str.strip().split()
        if len(args) < 2:
            yield event.plain_result("用法: /jmfolder [漫画ID] - 调试文件夹匹配")
            return

        comic_id = args[1]

        # 添加输入验证
        if not validate_comic_id(comic_id):
            yield event.plain_result("无效的漫画ID格式，请提供纯数字ID")
            return

        try:
            # 列出所有可能的目录
            debug_info = [f"🔍 调试漫画ID {comic_id} 的文件夹匹配:\n"]

            # 检查直接匹配
            direct_path = os.path.join(
                self.resource_manager.downloads_dir, str(comic_id)
            )
            direct_exists = os.path.exists(direct_path)
            debug_info.append(
                f"📁 直接匹配路径: {direct_path} - {'✅存在' if direct_exists else '❌不存在'}"
            )

            # 列出downloads目录中的所有文件夹
            if os.path.exists(self.resource_manager.downloads_dir):
                folders = [
                    f
                    for f in os.listdir(self.resource_manager.downloads_dir)
                    if os.path.isdir(
                        os.path.join(self.resource_manager.downloads_dir, f)
                    )
                ]

                debug_info.append(
                    f"\n📂 downloads目录中的所有文件夹 ({len(folders)}个):"
                )
                for folder in sorted(folders)[:10]:  # 只显示前10个
                    contains_id = str(comic_id) in folder
                    exact_match = (
                        folder.startswith(str(comic_id) + "_")
                        or folder.endswith("_" + str(comic_id))
                        or folder.startswith("[" + str(comic_id) + "]")
                        or folder == str(comic_id)
                    )

                    match_type = ""
                    if exact_match:
                        match_type = " ✅精确匹配"
                    elif contains_id:
                        # 检查是否是完整匹配
                        import re

                        pattern = r"\b" + re.escape(str(comic_id)) + r"\b"
                        if re.search(pattern, folder):
                            match_type = " 🔍部分匹配"
                        else:
                            match_type = " ⚠️包含但非完整匹配"

                    debug_info.append(f"  - {folder}{match_type}")

                if len(folders) > 10:
                    debug_info.append(f"  ... 还有 {len(folders) - 10} 个文件夹")

            # 显示实际查找结果
            actual_folder = self.resource_manager.find_comic_folder(comic_id)
            debug_info.append(f"\n🎯 实际匹配结果: {actual_folder}")
            debug_info.append(
                f"📊 匹配结果存在: {'✅是' if os.path.exists(actual_folder) else '❌否'}"
            )

            yield event.plain_result("\n".join(debug_info))

        except Exception as e:
            logger.error(f"调试文件夹匹配失败: {str(e)}")
            yield event.plain_result(f"调试失败: {str(e)}")

    async def terminate(self):
        """插件被卸载时清理资源"""
        logger.info("JM-Cosmos插件正在被卸载，执行资源清理...")
        # 清理线程池
        if hasattr(self, "downloader") and hasattr(self.downloader, "_thread_pool"):
            self.downloader._thread_pool.shutdown(wait=True)
        pass
