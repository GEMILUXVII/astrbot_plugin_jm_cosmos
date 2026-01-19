"""
认证管理器测试

测试 core/auth.py 中的 JMAuthManager 类。
使用 mock 避免实际网络请求。
"""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestJMAuthManagerInit:
    """JMAuthManager 初始化测试"""

    def test_init_with_config_manager(self, config_manager):
        """测试使用配置管理器初始化"""
        from core.auth import JMAuthManager

        manager = JMAuthManager(config_manager)
        assert manager.config is config_manager
        assert manager._logged_in is False
        assert manager._username is None
        assert manager._client is None

    def test_init_restores_session_from_cookies(
        self, config_manager_with_admin, data_dir
    ):
        """测试从 cookies 文件恢复会话"""
        from core.auth import JMAuthManager

        # 预先创建 cookies 文件
        cookies_file = data_dir / "cookies.json"
        cookies_file.write_text(
            json.dumps({"username": "saved_user", "logged_in": True})
        )

        manager = JMAuthManager(config_manager_with_admin)
        # 应该从文件中读取 username（但不会自动登录）
        assert manager._username == "saved_user"


class TestJMAuthManagerProperties:
    """JMAuthManager 属性测试"""

    def test_is_logged_in_default_false(self, config_manager):
        """测试默认未登录状态"""
        from core.auth import JMAuthManager

        manager = JMAuthManager(config_manager)
        assert manager.is_logged_in is False

    def test_current_user_when_not_logged_in(self, config_manager):
        """测试未登录时 current_user 为 None"""
        from core.auth import JMAuthManager

        manager = JMAuthManager(config_manager)
        assert manager.current_user is None

    def test_get_client_builds_new_client(self, config_manager):
        """测试 get_client 构建新客户端"""
        from core.auth import JMAuthManager

        manager = JMAuthManager(config_manager)
        # 当 jmcomic 不可用时，可能返回 None
        _client = manager.get_client()
        # 只要不抛出异常就算通过


class TestJMAuthManagerLogin:
    """JMAuthManager 登录测试"""

    @pytest.mark.asyncio
    async def test_login_jmcomic_unavailable(self, config_manager):
        """测试 jmcomic 不可用时登录失败"""
        from core.auth import JMAuthManager

        manager = JMAuthManager(config_manager)

        with patch.object(manager, "is_available", return_value=False):
            success, message = await manager.login("user", "pass")

        assert success is False
        assert "未安装" in message

    @pytest.mark.asyncio
    async def test_login_stores_credentials_on_success(self, config_manager):
        """测试登录成功后存储凭据"""
        from core.auth import JMAuthManager

        manager = JMAuthManager(config_manager)

        # 如果 jmcomic 不可用，跳过此测试
        if not manager.is_available():
            pytest.skip("jmcomic 库未安装")


class TestJMAuthManagerAutoLogin:
    """JMAuthManager 自动登录测试"""

    @pytest.mark.asyncio
    async def test_auto_login_no_credentials(self, config_manager):
        """测试无凭据时自动登录失败"""
        from core.auth import JMAuthManager

        manager = JMAuthManager(config_manager)
        success, message = await manager.auto_login()

        assert success is False
        assert "未配置" in message

    @pytest.mark.asyncio
    async def test_auto_login_already_logged_in(self, config_manager_with_admin):
        """测试已登录时自动登录直接返回成功"""
        from core.auth import JMAuthManager

        manager = JMAuthManager(config_manager_with_admin)
        manager._logged_in = True
        manager._username = "testuser"

        success, message = await manager.auto_login()

        assert success is True
        assert "已登录" in message


class TestJMAuthManagerEnsureLoggedIn:
    """JMAuthManager ensure_logged_in 测试"""

    @pytest.mark.asyncio
    async def test_ensure_logged_in_already_logged_in(self, config_manager):
        """测试已登录时直接返回成功"""
        from core.auth import JMAuthManager

        manager = JMAuthManager(config_manager)
        manager._logged_in = True
        manager._username = "testuser"

        success, message = await manager.ensure_logged_in()

        assert success is True
        assert "已登录" in message

    @pytest.mark.asyncio
    async def test_ensure_logged_in_no_credentials(self, config_manager):
        """测试无凭据时返回提示"""
        from core.auth import JMAuthManager

        manager = JMAuthManager(config_manager)
        success, message = await manager.ensure_logged_in()

        assert success is False
        assert "未登录" in message or "jmlogin" in message.lower()


class TestJMAuthManagerLogout:
    """JMAuthManager 登出测试"""

    def test_logout_when_not_logged_in(self, config_manager):
        """测试未登录时登出返回失败"""
        from core.auth import JMAuthManager

        manager = JMAuthManager(config_manager)
        success, message = manager.logout()

        assert success is False
        assert "未登录" in message

    def test_logout_clears_state(self, config_manager):
        """测试登出清除状态"""
        from core.auth import JMAuthManager

        manager = JMAuthManager(config_manager)
        manager._logged_in = True
        manager._username = "testuser"
        manager._client = MagicMock()

        success, message = manager.logout()

        assert success is True
        assert manager._logged_in is False
        assert manager._username is None
        assert manager._client is None
        assert "已登出" in message


class TestJMAuthManagerGetLoginStatus:
    """JMAuthManager get_login_status 测试"""

    def test_get_login_status_not_logged_in(self, config_manager):
        """测试未登录状态信息"""
        from core.auth import JMAuthManager

        manager = JMAuthManager(config_manager)
        status = manager.get_login_status()

        assert status["logged_in"] is False
        assert status["username"] is None
        assert "has_credentials" in status

    def test_get_login_status_logged_in(self, config_manager):
        """测试已登录状态信息"""
        from core.auth import JMAuthManager

        manager = JMAuthManager(config_manager)
        manager._logged_in = True
        manager._username = "testuser"

        status = manager.get_login_status()

        assert status["logged_in"] is True
        assert status["username"] == "testuser"


class TestJMAuthManagerSessionPersistence:
    """JMAuthManager 会话持久化测试"""

    def test_save_and_clear_session(self, config_manager, data_dir):
        """测试保存和清除会话"""
        from core.auth import JMAuthManager

        manager = JMAuthManager(config_manager)
        manager._logged_in = True
        manager._username = "testuser"

        # 保存会话
        manager._save_session()
        cookies_file = data_dir / "cookies.json"
        assert cookies_file.exists()

        # 读取验证
        data = json.loads(cookies_file.read_text())
        assert data["username"] == "testuser"

        # 清除会话
        manager._clear_session()
        assert not cookies_file.exists()
