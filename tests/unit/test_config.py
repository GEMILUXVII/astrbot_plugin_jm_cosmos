"""
配置管理器测试

测试 core/base/config.py 中的 JMConfigManager 类。
"""

from pathlib import Path

import pytest


class TestConfigManagerDefaults:
    """配置管理器默认值测试"""

    def test_download_dir_relative_path(self, config_manager, data_dir):
        """测试相对路径下载目录"""
        download_dir = config_manager.download_dir
        assert download_dir.is_absolute()
        assert download_dir.exists()

    def test_download_dir_absolute_path(self, temp_dir, data_dir):
        """测试绝对路径下载目录"""
        from core.base import JMConfigManager

        abs_path = str(temp_dir / "custom_downloads")
        config = {"download_dir": abs_path}
        manager = JMConfigManager(config, data_dir)
        assert str(manager.download_dir) == abs_path

    def test_image_suffix_default(self, config_manager):
        """测试默认图片格式"""
        assert config_manager.image_suffix == ".jpg"

    def test_client_type_default(self, config_manager):
        """测试默认客户端类型"""
        assert config_manager.client_type == "api"

    def test_proxy_disabled_by_default(self, config_manager):
        """测试代理默认禁用"""
        assert config_manager.use_proxy is False
        assert config_manager.proxy_url == ""

    def test_concurrent_settings(self, config_manager):
        """测试并发设置"""
        assert config_manager.max_concurrent_photos == 3
        assert config_manager.max_concurrent_images == 5

    def test_pack_format_default(self, config_manager):
        """测试默认打包格式"""
        assert config_manager.pack_format == "zip"
        assert config_manager.pack_password == ""

    def test_auto_delete_default(self, config_manager):
        """测试自动删除默认启用"""
        assert config_manager.auto_delete_after_send is True

    def test_send_cover_preview_default(self, config_manager):
        """测试封面预览默认启用"""
        assert config_manager.send_cover_preview is True

    def test_admin_only_default(self, config_manager):
        """测试管理员限制默认禁用"""
        assert config_manager.admin_only is False

    def test_search_page_size_default(self, config_manager):
        """测试搜索页大小默认值"""
        assert config_manager.search_page_size == 5

    def test_debug_mode_default(self, config_manager):
        """测试调试模式默认禁用"""
        assert config_manager.debug_mode is False


class TestAdminPermissions:
    """管理员权限测试"""

    def test_admin_only_disabled_everyone_is_admin(self, config_manager):
        """管理员限制关闭时所有人都有权限"""
        assert config_manager.is_admin("any_user") is True
        assert config_manager.is_admin("12345") is True

    def test_admin_only_enabled_check_admin_list(self, config_manager_with_admin):
        """管理员限制开启时检查管理员列表"""
        assert config_manager_with_admin.is_admin("123456") is True
        assert config_manager_with_admin.is_admin("789012") is True
        assert config_manager_with_admin.is_admin("999999") is False

    def test_admin_list_parsing(self, config_manager_with_admin):
        """测试管理员列表解析"""
        admin_list = config_manager_with_admin.admin_list
        assert isinstance(admin_list, set)
        assert "123456" in admin_list
        assert "789012" in admin_list


class TestGroupPermissions:
    """群组权限测试"""

    def test_empty_groups_means_all_enabled(self, config_manager):
        """空群组列表表示所有群都启用"""
        assert config_manager.is_group_enabled("any_group") is True

    def test_specific_groups_enabled(self, config_manager_with_admin):
        """指定群组列表时只有列表中的群启用"""
        assert config_manager_with_admin.is_group_enabled("group1") is True
        assert config_manager_with_admin.is_group_enabled("group2") is True
        assert config_manager_with_admin.is_group_enabled("group3") is False

    def test_enabled_groups_parsing(self, config_manager_with_admin):
        """测试启用群组列表解析"""
        enabled_groups = config_manager_with_admin.enabled_groups
        assert isinstance(enabled_groups, set)
        assert "group1" in enabled_groups
        assert "group2" in enabled_groups


class TestCredentials:
    """凭据管理测试"""

    def test_no_credentials_by_default(self, config_manager):
        """默认没有配置凭据"""
        assert config_manager.has_credentials() is False
        assert config_manager.jm_username == ""
        assert config_manager.jm_password == ""

    def test_has_credentials_when_configured(self, config_manager_with_admin):
        """配置凭据后检测正常"""
        assert config_manager_with_admin.has_credentials() is True
        assert config_manager_with_admin.jm_username == "testuser"
        assert config_manager_with_admin.jm_password == "testpass"

    def test_cookies_file_path(self, config_manager, data_dir):
        """测试 cookies 文件路径"""
        cookies_file = config_manager.cookies_file
        assert cookies_file == data_dir / "cookies.json"


class TestCustomConfig:
    """自定义配置测试"""

    def test_custom_image_suffix(self, data_dir):
        """测试自定义图片格式"""
        from core.base import JMConfigManager

        config = {"image_suffix": ".webp"}
        manager = JMConfigManager(config, data_dir)
        assert manager.image_suffix == ".webp"

    def test_custom_pack_settings(self, data_dir):
        """测试自定义打包设置"""
        from core.base import JMConfigManager

        config = {"pack_format": "pdf", "pack_password": "secret123"}
        manager = JMConfigManager(config, data_dir)
        assert manager.pack_format == "pdf"
        assert manager.pack_password == "secret123"

    def test_proxy_configuration(self, data_dir):
        """测试代理配置"""
        from core.base import JMConfigManager

        config = {"use_proxy": True, "proxy_url": "http://127.0.0.1:7890"}
        manager = JMConfigManager(config, data_dir)
        assert manager.use_proxy is True
        assert manager.proxy_url == "http://127.0.0.1:7890"
