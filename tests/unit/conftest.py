"""
pytest 配置和共享 fixtures

提供测试所需的公共配置、临时目录和 mock 对象。
"""

import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ==================== Mock 外部依赖 ====================
# 在导入插件模块之前 mock 外部依赖

# Mock jmcomic 模块
mock_jm_option = MagicMock()
mock_jm_option.__class__.__name__ = "JmOption"
mock_jmcomic = MagicMock()
mock_jmcomic.JmOption = mock_jm_option
mock_jmcomic.JmModuleConfig = MagicMock()
mock_jmcomic.JmcomicText = MagicMock()

# 设置 __spec__ 以通过 importlib.util.find_spec 检查
import importlib.util

mock_spec = importlib.util.spec_from_loader("jmcomic", loader=None)
mock_jmcomic.__spec__ = mock_spec

sys.modules["jmcomic"] = mock_jmcomic

# Mock astrbot 模块
mock_logger = MagicMock()
mock_astrbot_api = MagicMock()
mock_astrbot_api.logger = mock_logger

sys.modules["astrbot"] = MagicMock()
sys.modules["astrbot.api"] = mock_astrbot_api
sys.modules["astrbot.api.logger"] = mock_logger

# 将插件目录添加到 Python 路径
PLUGIN_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

# 设置包层级结构以支持相对导入
# 创建一个虚拟的顶级包来容纳 core 和 utils
import types

# 创建顶级虚拟包
plugin_pkg = types.ModuleType("astrbot_plugin_jm_cosmos")
plugin_pkg.__path__ = [str(PLUGIN_ROOT)]
plugin_pkg.__package__ = "astrbot_plugin_jm_cosmos"
sys.modules["astrbot_plugin_jm_cosmos"] = plugin_pkg

# 预先导入核心模块并注册
from core import base as core_base
from core import constants as core_constants

# 设置 core 子包
core_pkg = types.ModuleType("astrbot_plugin_jm_cosmos.core")
core_pkg.__path__ = [str(PLUGIN_ROOT / "core")]
core_pkg.__package__ = "astrbot_plugin_jm_cosmos.core"
core_pkg.constants = core_constants
core_pkg.base = core_base
sys.modules["astrbot_plugin_jm_cosmos.core"] = core_pkg
sys.modules["astrbot_plugin_jm_cosmos.core.constants"] = core_constants

# 设置 utils 子包
utils_pkg = types.ModuleType("astrbot_plugin_jm_cosmos.utils")
utils_pkg.__path__ = [str(PLUGIN_ROOT / "utils")]
utils_pkg.__package__ = "astrbot_plugin_jm_cosmos.utils"
sys.modules["astrbot_plugin_jm_cosmos.utils"] = utils_pkg


@pytest.fixture
def temp_dir(tmp_path: Path) -> Path:
    """提供临时目录用于测试"""
    return tmp_path


@pytest.fixture
def sample_plugin_config() -> dict[str, Any]:
    """示例插件配置"""
    return {
        "download_dir": "./downloads",
        "image_suffix": ".jpg",
        "client_type": "api",
        "use_proxy": False,
        "proxy_url": "",
        "max_concurrent_photos": 3,
        "max_concurrent_images": 5,
        "pack_format": "zip",
        "pack_password": "",
        "auto_delete_after_send": True,
        "send_cover_preview": True,
        "admin_only": False,
        "admin_list": "",
        "enabled_groups": "",
        "search_page_size": 5,
        "debug_mode": False,
        "jm_username": "",
        "jm_password": "",
    }


@pytest.fixture
def config_with_admin() -> dict[str, Any]:
    """启用管理员限制的配置"""
    return {
        "download_dir": "./downloads",
        "image_suffix": ".jpg",
        "client_type": "api",
        "use_proxy": False,
        "proxy_url": "",
        "max_concurrent_photos": 3,
        "max_concurrent_images": 5,
        "pack_format": "zip",
        "pack_password": "",
        "auto_delete_after_send": True,
        "send_cover_preview": True,
        "admin_only": True,
        "admin_list": "123456,789012",
        "enabled_groups": "group1,group2",
        "search_page_size": 5,
        "debug_mode": False,
        "jm_username": "testuser",
        "jm_password": "testpass",
    }


@pytest.fixture
def data_dir(temp_dir: Path) -> Path:
    """模拟数据目录"""
    data_path = temp_dir / "data"
    data_path.mkdir(parents=True, exist_ok=True)
    return data_path


@pytest.fixture
def config_manager(sample_plugin_config: dict, data_dir: Path):
    """预配置的 JMConfigManager 实例"""
    from core.base import JMConfigManager

    return JMConfigManager(sample_plugin_config, data_dir)


@pytest.fixture
def config_manager_with_admin(config_with_admin: dict, data_dir: Path):
    """启用管理员限制的 JMConfigManager 实例"""
    from core.base import JMConfigManager

    return JMConfigManager(config_with_admin, data_dir)


# ==================== Mock Fixtures ====================


@pytest.fixture
def mock_jmcomic_available():
    """Mock jmcomic 库可用"""
    with patch.dict(sys.modules, {"jmcomic": MagicMock()}):
        yield


@pytest.fixture
def mock_album():
    """Mock 本子对象"""
    album = MagicMock()
    album.id = "123456"
    album.title = "测试本子标题"
    album.author = "测试作者"
    album.page_count = 100
    album.tags = ["标签1", "标签2"]
    album.__len__ = lambda self: 5  # 5 个章节
    return album


@pytest.fixture
def mock_photo():
    """Mock 章节对象"""
    photo = MagicMock()
    photo.id = "123456_1"
    photo.album_id = "123456"
    photo.title = "第1话"
    photo.images = [MagicMock() for _ in range(20)]
    return photo


@pytest.fixture
def sample_album_dict() -> dict:
    """示例本子信息字典"""
    return {
        "id": "123456",
        "title": "测试本子标题",
        "author": "测试作者",
        "tags": ["标签1", "标签2", "标签3"],
        "page_count": 150,
        "photo_count": 5,
        "description": "这是一个测试描述",
    }


@pytest.fixture
def sample_search_results() -> list[dict]:
    """示例搜索结果"""
    return [
        {"id": "111111", "title": "搜索结果1", "author": "作者A", "page_count": 50},
        {"id": "222222", "title": "搜索结果2", "author": "作者B", "page_count": 80},
        {"id": "333333", "title": "搜索结果3", "author": "作者C", "page_count": 120},
    ]
