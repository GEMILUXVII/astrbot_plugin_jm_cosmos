"""
JM Cosmos2 - AstrBot JM漫画下载插件

支持搜索、下载禁漫天堂的漫画本子，基于jmcomic库
"""

from pathlib import Path

import astrbot.api.message_components as Comp
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, StarTools, register

from .core import JMAuthManager, JMBrowser, JMConfigManager, JMDownloadManager, JMPacker
from .utils import MessageFormatter

# 插件名称常量
PLUGIN_NAME = "jm_cosmos2"


@register(
    "jm_cosmos2",
    "GEMILUXVII",
    "JM漫画下载插件 - 支持搜索、下载禁漫天堂的漫画本子，支持加密PDF/ZIP打包",
    "2.4.0",
    "https://github.com/GEMILUXVII/jm_cosmos2",
)
class JMCosmosPlugin(Star):
    """AstrBot JM漫画下载插件"""

    def __init__(self, context: Context, config: AstrBotConfig = None):
        super().__init__(context)
        self.config = config

        logger.info("正在初始化 JM Cosmos2 插件...")

        # 获取数据目录
        try:
            self.data_dir = StarTools.get_data_dir(PLUGIN_NAME)
            self.data_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"JM Cosmos2 数据目录: {self.data_dir}")
        except Exception as e:
            logger.error(f"获取数据目录失败: {e}")
            self.data_dir = Path(__file__).parent / "data"
            self.data_dir.mkdir(parents=True, exist_ok=True)

        # 初始化配置管理器
        self.config_manager = JMConfigManager(config, self.data_dir)

        # 初始化下载管理器
        self.download_manager = JMDownloadManager(self.config_manager)

        # 初始化浏览查询器
        self.browser = JMBrowser(self.config_manager)

        # 初始化认证管理器
        self.auth_manager = JMAuthManager(self.config_manager)

        # 调试模式
        self.debug_mode = self.config_manager.debug_mode
        if self.debug_mode:
            logger.warning("JM Cosmos2 调试模式已启用")

        logger.info("JM Cosmos2 插件初始化完成")

    def _check_permission(self, event: AstrMessageEvent) -> tuple[bool, str]:
        """
        检查用户权限

        Returns:
            (是否有权限, 错误消息)
        """
        user_id = event.get_sender_id()
        group_id = event.get_group_id()

        # 检查管理员权限
        if not self.config_manager.is_admin(user_id):
            return False, MessageFormatter.format_error("permission")

        # 检查群启用状态
        if group_id and not self.config_manager.is_group_enabled(group_id):
            return False, MessageFormatter.format_error("group_disabled")

        return True, ""

    @filter.command("jmhelp")
    async def help_command(self, event: AstrMessageEvent):
        """显示帮助信息"""
        yield event.plain_result(MessageFormatter.format_help())

    @filter.command("jm")
    async def download_album_command(
        self, event: AstrMessageEvent, album_id: str = None
    ):
        """
        下载指定ID的漫画本子

        用法: /jm <ID>
        示例: /jm 123456
        """
        # 权限检查
        has_perm, error_msg = self._check_permission(event)
        if not has_perm:
            yield event.plain_result(error_msg)
            return

        # 参数检查
        if album_id is None:
            yield event.plain_result(
                "❌ 请提供本子ID\n用法: /jm <ID>\n示例: /jm 123456"
            )
            return

        # 转换为字符串并验证ID格式
        album_id = str(album_id).strip()
        if not album_id.isdigit():
            yield event.plain_result(MessageFormatter.format_error("invalid_id"))
            return

        try:
            # 发送开始下载提示
            yield event.plain_result(f"⏳ 开始下载本子 {album_id}，请稍候...")

            # 如果配置了发送封面预览，先获取详情和封面
            if self.config_manager.send_cover_preview:
                detail = await self.browser.get_album_detail(album_id)
                if detail:
                    # 获取封面图片
                    cover_dir = self.config_manager.download_dir / "covers"
                    cover_path = await self.browser.get_album_cover(album_id, cover_dir)

                    if cover_path and cover_path.exists():
                        yield event.chain_result(
                            [
                                Comp.Image(file=str(cover_path)),
                                Comp.Plain(MessageFormatter.format_album_info(detail)),
                            ]
                        )
                    else:
                        yield event.plain_result(MessageFormatter.format_album_info(detail))

            # 执行下载
            result = await self.download_manager.download_album(album_id)

            if not result.success:
                yield event.plain_result(
                    MessageFormatter.format_error(
                        "download_failed", result.error_message
                    )
                )
                return

            # 打包文件
            packer = JMPacker(
                pack_format=self.config_manager.pack_format,
                password=self.config_manager.pack_password,
            )

            pack_result = packer.pack(
                source_dir=result.save_path,
                output_name=f"JM{album_id}_{result.title[:20]}",
            )

            # 发送结果消息
            result_msg = MessageFormatter.format_download_result(result, pack_result)

            if (
                pack_result.success
                and pack_result.output_path
                and pack_result.format != "none"
            ):
                # 发送打包后的文件
                yield event.chain_result(
                    [
                        Comp.Plain(result_msg),
                        Comp.File(
                            name=pack_result.output_path.name,
                            file=str(pack_result.output_path),
                        ),
                    ]
                )

                # 自动清理
                if self.config_manager.auto_delete_after_send:
                    JMPacker.cleanup(result.save_path)
                    JMPacker.cleanup(pack_result.output_path)
            else:
                yield event.plain_result(result_msg)

        except Exception as e:
            logger.error(f"下载本子失败: {e}")
            if self.debug_mode:
                import traceback

                logger.error(traceback.format_exc())
            yield event.plain_result(
                MessageFormatter.format_error("download_failed", str(e))
            )

    @filter.command("jmc")
    async def download_photo_command(
        self, event: AstrMessageEvent, photo_id: str = None
    ):
        """
        下载指定ID的章节

        用法: /jmc <ID>
        示例: /jmc 789012
        """
        # 权限检查
        has_perm, error_msg = self._check_permission(event)
        if not has_perm:
            yield event.plain_result(error_msg)
            return

        if photo_id is None:
            yield event.plain_result(
                "❌ 请提供章节ID\n用法: /jmc <ID>\n示例: /jmc 789012"
            )
            return

        photo_id = str(photo_id).strip()
        if not photo_id.isdigit():
            yield event.plain_result(MessageFormatter.format_error("invalid_id"))
            return

        try:
            yield event.plain_result(f"⏳ 开始下载章节 {photo_id}，请稍候...")

            result = await self.download_manager.download_photo(photo_id)

            if not result.success:
                yield event.plain_result(
                    MessageFormatter.format_error(
                        "download_failed", result.error_message
                    )
                )
                return

            # 打包
            packer = JMPacker(
                pack_format=self.config_manager.pack_format,
                password=self.config_manager.pack_password,
            )

            pack_result = packer.pack(
                source_dir=result.save_path, output_name=f"JM_photo_{photo_id}"
            )

            result_msg = MessageFormatter.format_download_result(result, pack_result)

            if (
                pack_result.success
                and pack_result.output_path
                and pack_result.format != "none"
            ):
                yield event.chain_result(
                    [
                        Comp.Plain(result_msg),
                        Comp.File(
                            name=pack_result.output_path.name,
                            file=str(pack_result.output_path),
                        ),
                    ]
                )

                if self.config_manager.auto_delete_after_send:
                    JMPacker.cleanup(result.save_path)
                    JMPacker.cleanup(pack_result.output_path)
            else:
                yield event.plain_result(result_msg)

        except Exception as e:
            logger.error(f"下载章节失败: {e}")
            yield event.plain_result(
                MessageFormatter.format_error("download_failed", str(e))
            )

    @filter.command("jms")
    async def search_command(self, event: AstrMessageEvent, keyword: str = None):
        """
        搜索漫画

        用法: /jms <关键词>
        示例: /jms 标签名
        """
        # 权限检查
        has_perm, error_msg = self._check_permission(event)
        if not has_perm:
            yield event.plain_result(error_msg)
            return

        if keyword is None:
            yield event.plain_result(
                "❌ 请提供搜索关键词\n用法: /jms <关键词>\n示例: /jms 标签名"
            )
            return

        keyword = str(keyword).strip()
        if not keyword:
            yield event.plain_result("❌ 搜索关键词不能为空")
            return

        try:
            yield event.plain_result(f"🔍 正在搜索: {keyword}...")

            results = await self.browser.search_albums(keyword)

            # 限制结果数量
            page_size = self.config_manager.search_page_size
            results = results[:page_size]

            result_msg = MessageFormatter.format_search_results(results, keyword)
            yield event.plain_result(result_msg)

        except Exception as e:
            logger.error(f"搜索失败: {e}")
            yield event.plain_result(MessageFormatter.format_error("network", str(e)))

    @filter.command("jmi")
    async def info_command(self, event: AstrMessageEvent, album_id: str = None):
        """
        查看本子详情

        用法: /jmi <ID>
        示例: /jmi 123456
        """
        # 权限检查
        has_perm, error_msg = self._check_permission(event)
        if not has_perm:
            yield event.plain_result(error_msg)
            return

        if album_id is None:
            yield event.plain_result(
                "❌ 请提供本子ID\n用法: /jmi <ID>\n示例: /jmi 123456"
            )
            return

        album_id = str(album_id).strip()
        if not album_id.isdigit():
            yield event.plain_result(MessageFormatter.format_error("invalid_id"))
            return

        try:
            yield event.plain_result(f"📖 正在获取本子 {album_id} 的详情...")

            detail = await self.browser.get_album_detail(album_id)

            if not detail:
                yield event.plain_result(MessageFormatter.format_error("not_found"))
                return

            # 获取封面图片
            cover_dir = self.config_manager.download_dir / "covers"
            cover_path = await self.browser.get_album_cover(album_id, cover_dir)

            if cover_path and cover_path.exists():
                yield event.chain_result(
                    [
                        Comp.Image(file=str(cover_path)),
                        Comp.Plain(MessageFormatter.format_album_info(detail)),
                    ]
                )
            else:
                yield event.plain_result(MessageFormatter.format_album_info(detail))

        except Exception as e:
            logger.error(f"获取详情失败: {e}")
            yield event.plain_result(MessageFormatter.format_error("network", str(e)))

    @filter.command("jmrank")
    async def ranking_command(
        self, event: AstrMessageEvent, ranking_type: str = "week", page: int = 1
    ):
        """
        查看排行榜

        用法: /jmrank [week/month] [页码]
        示例: /jmrank week 1
        """
        # 权限检查
        has_perm, error_msg = self._check_permission(event)
        if not has_perm:
            yield event.plain_result(error_msg)
            return

        # 验证排行榜类型
        ranking_type = str(ranking_type).lower().strip()
        if ranking_type not in ("week", "month"):
            yield event.plain_result(
                "❌ 无效的排行榜类型\n用法: /jmrank [week/month] [页码]\n示例: /jmrank week 1"
            )
            return

        # 验证页码
        try:
            page = int(page)
            if page < 1:
                page = 1
        except (ValueError, TypeError):
            page = 1

        try:
            type_name = "周" if ranking_type == "week" else "月"
            yield event.plain_result(f"🏆 正在获取{type_name}排行榜第{page}页...")

            if ranking_type == "week":
                results = await self.browser.get_week_ranking(page)
            else:
                results = await self.browser.get_month_ranking(page)

            # 限制结果数量
            page_size = self.config_manager.search_page_size
            results = results[:page_size]

            result_msg = MessageFormatter.format_ranking_results(
                results, ranking_type, page
            )
            yield event.plain_result(result_msg)

        except Exception as e:
            logger.error(f"获取排行榜失败: {e}")
            yield event.plain_result(MessageFormatter.format_error("network", str(e)))

    @filter.command("jmlogin")
    async def login_command(
        self, event: AstrMessageEvent, username: str = None, password: str = None
    ):
        """
        登录JM账号

        用法: /jmlogin <用户名> <密码>
        示例: /jmlogin myuser mypass
        """
        # 权限检查
        has_perm, error_msg = self._check_permission(event)
        if not has_perm:
            yield event.plain_result(error_msg)
            return

        # 参数检查
        if username is None or password is None:
            yield event.plain_result(
                "❌ 请提供用户名和密码\n用法: /jmlogin <用户名> <密码>\n示例: /jmlogin myuser mypass"
            )
            return

        try:
            yield event.plain_result("🔐 正在登录...")

            success, message = await self.auth_manager.login(username, password)

            if success:
                yield event.plain_result(f"✅ {message}")
            else:
                yield event.plain_result(f"❌ {message}")

        except Exception as e:
            logger.error(f"登录失败: {e}")
            yield event.plain_result(MessageFormatter.format_error("network", str(e)))

    @filter.command("jmlogout")
    async def logout_command(self, event: AstrMessageEvent):
        """
        登出JM账号

        用法: /jmlogout
        """
        # 权限检查
        has_perm, error_msg = self._check_permission(event)
        if not has_perm:
            yield event.plain_result(error_msg)
            return

        success, message = self.auth_manager.logout()

        if success:
            yield event.plain_result(f"✅ {message}")
        else:
            yield event.plain_result(f"❌ {message}")

    @filter.command("jmstatus")
    async def status_command(self, event: AstrMessageEvent):
        """
        查看登录状态

        用法: /jmstatus
        """
        # 权限检查
        has_perm, error_msg = self._check_permission(event)
        if not has_perm:
            yield event.plain_result(error_msg)
            return

        status = self.auth_manager.get_login_status()

        if status["logged_in"]:
            yield event.plain_result(f"✅ 已登录\n👤 用户名: {status['username']}")
        else:
            yield event.plain_result(
                "❌ 当前未登录\n💡 使用 /jmlogin <用户名> <密码> 登录"
            )

    @filter.command("jmfav")
    async def favorites_command(
        self, event: AstrMessageEvent, page: int = 1, folder_id: str = "0"
    ):
        """
        查看我的收藏

        用法: /jmfav [页码] [收藏夹ID]
        示例: /jmfav 1
        """
        # 权限检查
        has_perm, error_msg = self._check_permission(event)
        if not has_perm:
            yield event.plain_result(error_msg)
            return

        # 检查登录状态
        logged_in, login_msg = await self.auth_manager.ensure_logged_in()
        if not logged_in:
            yield event.plain_result(f"❌ {login_msg}\n💡 请先使用 /jmlogin 登录")
            return

        # 验证页码
        try:
            page = int(page)
            if page < 1:
                page = 1
        except (ValueError, TypeError):
            page = 1

        try:
            yield event.plain_result(f"⭐ 正在获取收藏夹第{page}页...")

            client = self.auth_manager.get_client()
            albums, folders = await self.browser.get_favorites(client, page, folder_id)

            result_msg = MessageFormatter.format_favorites(albums, folders, page)
            yield event.plain_result(result_msg)

        except Exception as e:
            logger.error(f"获取收藏夹失败: {e}")
            yield event.plain_result(MessageFormatter.format_error("network", str(e)))
