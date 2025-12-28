"""
JMComic 客户端管理模块

提供底层客户端管理的公共逻辑，供 downloader 和 browser 模块使用。
"""

import asyncio
import importlib.util
from collections.abc import Callable
from typing import TypeVar

from .config import JMConfigManager

# 泛型类型，用于标注返回值
T = TypeVar("T")

JMCOMIC_AVAILABLE = importlib.util.find_spec("jmcomic") is not None

if JMCOMIC_AVAILABLE:
    from jmcomic import JmOption
else:
    JmOption = None


class JMClientMixin:
    """
    JMComic 客户端混入类

    提供统一的客户端管理和异步执行模式。
    子类需要提供 config 属性（JMConfigManager 实例）。
    """

    config: JMConfigManager

    def _get_option(self) -> JmOption | None:
        """获取 JmOption 配置"""
        return self.config.get_option()

    def _build_client(self, option: JmOption | None = None):
        """构建 JM 客户端"""
        if option is None:
            option = self._get_option()
        if option is None:
            return None
        return option.build_jm_client()

    async def _run_sync(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        在线程池中运行同步函数

        Args:
            func: 要执行的同步函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数返回值
        """
        return await asyncio.to_thread(func, *args, **kwargs)

    @staticmethod
    def is_available() -> bool:
        """检查 jmcomic 库是否可用"""
        return JMCOMIC_AVAILABLE
