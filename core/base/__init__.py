"""
JM-Cosmos II 基础模块

提供配置管理和客户端混入类。
"""

from .client import JMClientMixin
from .config import JMConfigManager

__all__ = ["JMClientMixin", "JMConfigManager"]
