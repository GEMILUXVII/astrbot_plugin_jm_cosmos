"""
JMComic 认证管理模块

提供登录、登出、会话管理等认证功能，支持 cookies 持久化。
"""

import json

from astrbot.api import logger

from .base import JMClientMixin, JMConfigManager


class JMAuthManager(JMClientMixin):
    """JMComic 认证管理器"""

    def __init__(self, config_manager: JMConfigManager):
        """
        初始化认证管理器

        Args:
            config_manager: 配置管理器实例
        """
        self.config = config_manager
        self._logged_in = False
        self._username: str | None = None
        self._client = None

        # 尝试从 cookies 文件恢复登录状态
        self._try_restore_session()

    def _try_restore_session(self) -> None:
        """尝试从 cookies 文件恢复登录状态"""
        cookies_file = self.config.cookies_file
        if cookies_file.exists():
            try:
                with open(cookies_file, encoding="utf-8") as f:
                    data = json.load(f)
                    if data.get("username"):
                        self._username = data["username"]
                        # 标记为需要重新验证
                        logger.info(f"发现已保存的登录信息: {self._username}")
            except Exception as e:
                logger.debug(f"读取 cookies 文件失败: {e}")

    def _save_session(self) -> None:
        """保存登录会话到文件"""
        if not self._logged_in or not self._username:
            return

        cookies_file = self.config.cookies_file
        try:
            data = {
                "username": self._username,
                "logged_in": True,
            }
            with open(cookies_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug(f"登录信息已保存到: {cookies_file}")
        except Exception as e:
            logger.error(f"保存登录信息失败: {e}")

    def _clear_session(self) -> None:
        """清除保存的登录会话"""
        cookies_file = self.config.cookies_file
        if cookies_file.exists():
            try:
                cookies_file.unlink()
                logger.debug("已清除保存的登录信息")
            except Exception as e:
                logger.error(f"清除登录信息失败: {e}")

    @property
    def is_logged_in(self) -> bool:
        """检查是否已登录"""
        return self._logged_in

    @property
    def current_user(self) -> str | None:
        """获取当前登录用户名"""
        return self._username if self._logged_in else None

    def get_client(self):
        """获取已认证的客户端（如果已登录）"""
        if self._logged_in and self._client is not None:
            return self._client
        return self._build_client()

    async def login(self, username: str, password: str) -> tuple[bool, str]:
        """
        异步登录

        Args:
            username: 用户名
            password: 密码

        Returns:
            (成功与否, 消息)
        """
        if not self.is_available():
            return False, "jmcomic 库未安装"

        try:
            result = await self._run_sync(self._login_sync, username, password)
            return result
        except Exception as e:
            logger.error(f"登录失败: {e}")
            return False, f"登录失败: {str(e)}"

    def _login_sync(self, username: str, password: str) -> tuple[bool, str]:
        """同步登录"""
        try:
            option = self._get_option()
            if option is None:
                return False, "无法创建配置"

            client = option.build_jm_client()
            client.login(username, password)

            # 保存登录状态
            self._logged_in = True
            self._username = username
            self._client = client

            # 持久化保存
            self._save_session()

            logger.info(f"用户 {username} 登录成功")
            return True, f"登录成功，欢迎 {username}！"

        except Exception as e:
            error_msg = str(e)
            logger.error(f"登录失败: {error_msg}")

            # 解析常见错误
            if "password" in error_msg.lower() or "用户名" in error_msg:
                return False, "用户名或密码错误"
            elif "network" in error_msg.lower() or "connect" in error_msg.lower():
                return False, "网络连接失败，请稍后重试"

            return False, f"登录失败: {error_msg}"

    async def auto_login(self) -> tuple[bool, str]:
        """
        使用配置的凭据自动登录

        Returns:
            (成功与否, 消息)
        """
        if not self.config.has_credentials():
            return False, "未配置登录凭据"

        if self._logged_in:
            return True, f"已登录: {self._username}"

        return await self.login(self.config.jm_username, self.config.jm_password)

    async def ensure_logged_in(self) -> tuple[bool, str]:
        """
        确保已登录（如果未登录则尝试自动登录）

        Returns:
            (成功与否, 消息)
        """
        if self._logged_in:
            return True, f"已登录: {self._username}"

        # 尝试使用配置的凭据自动登录
        if self.config.has_credentials():
            return await self.auto_login()

        return False, "未登录，请使用 /jmlogin 登录"

    def logout(self) -> tuple[bool, str]:
        """
        登出

        Returns:
            (成功与否, 消息)
        """
        if not self._logged_in:
            return False, "当前未登录"

        username = self._username
        self._logged_in = False
        self._username = None
        self._client = None

        # 清除保存的会话
        self._clear_session()

        logger.info(f"用户 {username} 已登出")
        return True, f"已登出账号 {username}"

    def get_login_status(self) -> dict:
        """
        获取登录状态

        Returns:
            登录状态信息字典
        """
        return {
            "logged_in": self._logged_in,
            "username": self._username,
            "has_credentials": self.config.has_credentials(),
        }
