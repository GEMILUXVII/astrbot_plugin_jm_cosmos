"""
JMComic 配置管理模块
"""

import importlib.util
import os
from pathlib import Path
from typing import Any

JMCOMIC_AVAILABLE = importlib.util.find_spec("jmcomic") is not None

if JMCOMIC_AVAILABLE:
    from jmcomic import JmModuleConfig, JmOption
else:
    JmOption = None


class JMConfigManager:
    """JMComic 配置管理器"""

    def __init__(self, plugin_config: dict[str, Any], data_dir: Path):
        """
        初始化配置管理器

        Args:
            plugin_config: AstrBot插件配置
            data_dir: 插件数据目录
        """
        self.plugin_config = plugin_config
        self.data_dir = data_dir
        self._option: JmOption | None = None

    @property
    def download_dir(self) -> Path:
        """获取下载目录"""
        dir_path = self.plugin_config.get("download_dir", "./downloads")
        if not os.path.isabs(dir_path):
            dir_path = self.data_dir / dir_path
        else:
            dir_path = Path(dir_path)
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path

    @property
    def image_suffix(self) -> str:
        """获取图片格式"""
        return self.plugin_config.get("image_suffix", ".jpg")

    @property
    def client_type(self) -> str:
        """获取客户端类型"""
        return self.plugin_config.get("client_type", "api")

    @property
    def use_proxy(self) -> bool:
        """是否使用代理"""
        return self.plugin_config.get("use_proxy", False)

    @property
    def proxy_url(self) -> str:
        """获取代理地址"""
        return self.plugin_config.get("proxy_url", "")

    @property
    def max_concurrent_photos(self) -> int:
        """最大并发章节数"""
        return self.plugin_config.get("max_concurrent_photos", 3)

    @property
    def max_concurrent_images(self) -> int:
        """最大并发图片数"""
        return self.plugin_config.get("max_concurrent_images", 5)

    @property
    def pack_format(self) -> str:
        """打包格式"""
        return self.plugin_config.get("pack_format", "zip")

    @property
    def pack_password(self) -> str:
        """打包密码"""
        return self.plugin_config.get("pack_password", "")

    @property
    def filename_show_password(self) -> bool:
        """是否在文件名中显示密码提示"""
        return self.plugin_config.get("filename_show_password", False)

    @property
    def auto_delete_after_send(self) -> bool:
        """发送后是否自动删除"""
        return self.plugin_config.get("auto_delete_after_send", True)

    @property
    def send_cover_preview(self) -> bool:
        """是否发送封面预览"""
        return self.plugin_config.get("send_cover_preview", True)

    @property
    def admin_only(self) -> bool:
        """是否仅管理员可用"""
        return self.plugin_config.get("admin_only", False)

    @property
    def admin_list(self) -> set:
        """管理员列表"""
        admin_str = self.plugin_config.get("admin_list", "")
        return {a.strip() for a in admin_str.split(",") if a.strip()}

    @property
    def enabled_groups(self) -> set:
        """启用的群列表"""
        groups_str = self.plugin_config.get("enabled_groups", "")
        if not groups_str:
            return set()  # 空集合表示所有群都启用
        return {g.strip() for g in groups_str.split(",") if g.strip()}

    @property
    def search_page_size(self) -> int:
        """搜索结果每页数量"""
        return self.plugin_config.get("search_page_size", 5)

    @property
    def debug_mode(self) -> bool:
        """调试模式"""
        return self.plugin_config.get("debug_mode", False)

    @property
    def jm_username(self) -> str:
        """JM账号用户名"""
        return self.plugin_config.get("jm_username", "")

    @property
    def jm_password(self) -> str:
        """JM账号密码"""
        return self.plugin_config.get("jm_password", "")

    @property
    def auto_recall_enabled(self) -> bool:
        """是否启用自动撤回"""
        return self.plugin_config.get("auto_recall_enabled", False)

    @property
    def auto_recall_delay(self) -> int:
        """自动撤回延迟（秒）"""
        return self.plugin_config.get("auto_recall_delay", 60)

    @property
    def cookies_file(self) -> Path:
        """Cookies文件路径"""
        return self.data_dir / "cookies.json"

    def has_credentials(self) -> bool:
        """检查是否配置了登录凭据"""
        return bool(self.jm_username and self.jm_password)

    def is_admin(self, user_id: str) -> bool:
        """检查用户是否是管理员"""
        if not self.admin_only:
            return True  # 如果没开启管理员限制，所有人都有权限
        return str(user_id) in self.admin_list

    def is_group_enabled(self, group_id: str) -> bool:
        """检查群是否启用"""
        if not self.enabled_groups:
            return True  # 空集合表示所有群都启用
        return str(group_id) in self.enabled_groups

    def create_jm_option(self) -> JmOption | None:
        """
        创建 JmOption 配置对象

        Returns:
            JmOption 实例，如果jmcomic未安装则返回None
        """
        if not JMCOMIC_AVAILABLE:
            return None

        if self._option is not None:
            return self._option

        # 构建配置字典
        option_dict = {
            "dir_rule": {"base_dir": str(self.download_dir), "rule": "Bd/Atitle"},
            "download": {
                "image": {"suffix": self.image_suffix},
                "threading": {
                    "photo": self.max_concurrent_photos,
                    "image": self.max_concurrent_images,
                },
            },
            "client": {"impl": self.client_type},
        }

        # 添加代理配置
        # 修复 #43: Docker 环境下需要显式禁用代理，否则 jmcomic 会使用默认的系统代理
        if self.use_proxy and self.proxy_url:
            option_dict["client"]["postman"] = {
                "meta_data": {"proxies": self.proxy_url}
            }
        else:
            # 显式禁用代理，覆盖 jmcomic 的默认系统代理设置
            option_dict["client"]["postman"] = {
                "meta_data": {"proxies": {}}
            }

        # 使用字典构建 JmOption
        self._option = JmModuleConfig.option_class().construct(option_dict)
        return self._option

    def get_option(self) -> JmOption | None:
        """获取或创建 JmOption"""
        if self._option is None:
            self._option = self.create_jm_option()
        return self._option
