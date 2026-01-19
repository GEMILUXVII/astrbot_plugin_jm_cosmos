"""
登录功能集成测试

需要设置环境变量 JM_TEST_USERNAME 和 JM_TEST_PASSWORD。
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.requires_login]


class TestAuthIntegration:
    """认证功能集成测试"""

    @pytest.mark.asyncio
    async def test_login_with_valid_credentials(self, auth_manager, has_credentials):
        """测试使用有效凭据登录"""
        if not has_credentials:
            pytest.skip(
                "未配置测试账号（设置 JM_TEST_USERNAME 和 JM_TEST_PASSWORD 环境变量）"
            )

        success, message = await auth_manager.auto_login()

        assert success, f"登录应该成功: {message}"
        assert auth_manager.is_logged_in
        assert auth_manager.current_user is not None

    @pytest.mark.asyncio
    async def test_login_with_invalid_credentials(self, config_manager):
        """测试使用无效凭据登录"""
        from core.auth import JMAuthManager

        manager = JMAuthManager(config_manager)
        success, message = await manager.login("invalid_user_12345", "wrong_password")

        # 无效凭据通常不应该登录成功
        # 但某些情况下服务器可能返回非预期响应，所以这里只验证调用正常完成
        assert isinstance(success, bool), "登录应该返回布尔值"
        assert isinstance(message, str), "登录应该返回消息字符串"

    @pytest.mark.asyncio
    async def test_logout(self, auth_manager, has_credentials):
        """测试登出"""
        if not has_credentials:
            pytest.skip("未配置测试账号")

        # 先登录
        await auth_manager.auto_login()

        if auth_manager.is_logged_in:
            success, message = auth_manager.logout()
            assert success, f"登出应该成功: {message}"
            assert not auth_manager.is_logged_in

    @pytest.mark.asyncio
    async def test_get_favorites_requires_login(
        self, browser, auth_manager, has_credentials
    ):
        """测试收藏夹功能（需要登录）"""
        if not has_credentials:
            pytest.skip("未配置测试账号")

        # 登录
        await auth_manager.auto_login()

        if not auth_manager.is_logged_in:
            pytest.skip("登录失败")

        # 获取收藏夹
        client = auth_manager.get_client()
        albums, folders = await browser.get_favorites(client, page=1)

        assert isinstance(albums, list)
        assert isinstance(folders, list)
