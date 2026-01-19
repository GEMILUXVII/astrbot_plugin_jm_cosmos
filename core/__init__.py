"""
JM-Cosmos II 核心模块

提供下载、浏览、认证、配置、打包、配额等核心功能。
"""

import importlib.util

from .auth import JMAuthManager
from .base import JMClientMixin, JMConfigManager
from .browser import JMBrowser
from .downloader import DownloadResult, JMDownloadManager
from .packer import JMPacker
from .quota import DownloadQuotaManager

# 集中管理 jmcomic 库的可用性检查
JMCOMIC_AVAILABLE = importlib.util.find_spec("jmcomic") is not None

__all__ = [
    "JMCOMIC_AVAILABLE",
    "DownloadQuotaManager",
    "JMAuthManager",
    "JMBrowser",
    "JMClientMixin",
    "JMConfigManager",
    "JMDownloadManager",
    "DownloadResult",
    "JMPacker",
]
