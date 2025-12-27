"""
JMComic 认证管理模块

提供登录、登出、会话管理等认证功能。
"""

from astrbot.api import logger

from .base import JMClientMixin, JMConfigManager

try:
    JMCOMIC_AVAILABLE = True
except ImportError:
    JMCOMIC_AVAILABLE = False


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
        }
