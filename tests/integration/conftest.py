"""
集成测试配置

使用真实 jmcomic 库连接 JM 服务器进行测试。
"""

import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

# ==================== 清除单元测试的 mock ====================
# 单元测试的 conftest.py 可能已经 mock 了 jmcomic
# 在集成测试中我们需要使用真实的库

# 清除 jmcomic 相关的 mock
for mod_name in list(sys.modules.keys()):
    if mod_name == "jmcomic" or mod_name.startswith("jmcomic."):
        # 检查是否是 mock 对象
        if hasattr(sys.modules[mod_name], "_mock_name") or "MagicMock" in str(type(sys.modules[mod_name])):
            del sys.modules[mod_name]

# 同时清除可能被缓存的 core 模块
for mod_name in list(sys.modules.keys()):
    if mod_name.startswith("core."):
        del sys.modules[mod_name]

# ==================== Mock astrbot 依赖 ====================
# astrbot 是 AstrBot 框架的模块，在测试环境中不可用
# 但我们使用真实的 jmcomic 库

mock_logger = MagicMock()
mock_astrbot_api = MagicMock()
mock_astrbot_api.logger = mock_logger

sys.modules["astrbot"] = MagicMock()
sys.modules["astrbot.api"] = mock_astrbot_api
sys.modules["astrbot.api.logger"] = mock_logger

# 将插件目录添加到 Python 路径
PLUGIN_ROOT = Path(__file__).parent.parent.parent
TESTS_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))

# ==================== 加载 .env 文件 ====================
# 从 tests/.env 文件读取测试账号配置
env_file = TESTS_ROOT / ".env"
if env_file.exists():
    with open(env_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

# 测试用的默认漫画 ID（体积小，适合测试）
TEST_ALBUM_ID = "2568"

# 从环境变量读取测试账号
TEST_USERNAME = os.environ.get("JM_TEST_USERNAME", "")
TEST_PASSWORD = os.environ.get("JM_TEST_PASSWORD", "")


def pytest_configure(config):
    """注册自定义 markers"""
    config.addinivalue_line("markers", "integration: 集成测试（需要网络连接）")
    config.addinivalue_line("markers", "slow: 慢速测试")
    config.addinivalue_line("markers", "requires_login: 需要登录账号的测试")


@pytest.fixture(scope="session")
def temp_download_dir(tmp_path_factory) -> Path:
    """创建临时下载目录"""
    return tmp_path_factory.mktemp("downloads")


@pytest.fixture(scope="session")
def integration_config(temp_download_dir: Path) -> dict[str, Any]:
    """集成测试配置"""
    return {
        "download_dir": str(temp_download_dir),
        "image_suffix": ".jpg",
        "client_type": "api",
        "use_proxy": False,
        "proxy_url": "",
        "max_concurrent_photos": 2,
        "max_concurrent_images": 3,
        "pack_format": "zip",
        "pack_password": "",
        "auto_delete_after_send": False,
        "send_cover_preview": True,
        "admin_only": False,
        "admin_list": "",
        "enabled_groups": "",
        "search_page_size": 5,
        "debug_mode": True,
        "jm_username": TEST_USERNAME,
        "jm_password": TEST_PASSWORD,
    }


@pytest.fixture(scope="session")
def config_manager(integration_config: dict, temp_download_dir: Path):
    """真实的 JMConfigManager 实例"""
    from core.base import JMConfigManager

    return JMConfigManager(integration_config, temp_download_dir)


@pytest.fixture(scope="session")
def browser(config_manager):
    """真实的 JMBrowser 实例"""
    from core.browser import JMBrowser

    return JMBrowser(config_manager)


@pytest.fixture(scope="session")
def downloader(config_manager):
    """真实的 JMDownloadManager 实例"""
    from core.downloader import JMDownloadManager

    return JMDownloadManager(config_manager)


@pytest.fixture(scope="session")
def auth_manager(config_manager):
    """真实的 JMAuthManager 实例"""
    from core.auth import JMAuthManager

    return JMAuthManager(config_manager)


@pytest.fixture
def test_album_id() -> str:
    """测试用的漫画 ID"""
    return TEST_ALBUM_ID


@pytest.fixture
def has_credentials() -> bool:
    """检查是否配置了测试账号"""
    return bool(TEST_USERNAME and TEST_PASSWORD)
