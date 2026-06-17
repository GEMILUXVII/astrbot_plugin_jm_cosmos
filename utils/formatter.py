"""
消息格式化工具
"""

from ..core.constants import CATEGORY_NAMES, ORDER_NAMES, TIME_NAMES


class MessageFormatter:
    """消息格式化器"""

    @staticmethod
    def format_album_info(album: dict) -> str:
        """
        格式化本子信息

        Args:
            album: 本子信息字典

        Returns:
            格式化后的字符串
        """
        lines = [
            f"📖 {album.get('title', '未知标题')}",
            "━━━━━━━━━━━━━━━━━━━━━",
            f"🆔 ID: {album.get('id', 'N/A')}",
            f"✍️ 作者: {album.get('author', '未知')}",
            f"📚 章节数: {album.get('photo_count', 0)}",
        ]

        if album.get("tags"):
            tags = album["tags"][:5]  # 最多显示5个标签
            lines.append(f"🏷️ 标签: {', '.join(tags)}")

        if album.get("pub_date"):
            lines.append(f"📅 发布: {album['pub_date']}")

        if album.get("update_date"):
            lines.append(f"🔄 更新: {album['update_date']}")

        if album.get("likes"):
            lines.append(f"❤️ 点赞: {album['likes']}")

        if album.get("views"):
            lines.append(f"👁️ 浏览: {album['views']}")

        if album.get("description"):
            desc = album["description"][:100]
            if len(album["description"]) > 100:
                desc += "..."
            lines.append(f"📝 简介: {desc}")

        lines.append("━━━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 使用 /jm <ID> 下载此本子")

        return "\n".join(lines)

    @staticmethod
    def format_search_results(results: list[dict], keyword: str, page: int = 1) -> str:
        """
        格式化搜索结果

        Args:
            results: 搜索结果列表
            keyword: 搜索关键词
            page: 当前页码

        Returns:
            格式化后的字符串
        """
        if not results:
            return f'🔍 未找到与 "{keyword}" 相关的结果'

        lines = [
            f"🔍 搜索: {keyword} (第{page}页)",
            "━━━━━━━━━━━━━━━━━━━━━",
        ]

        for i, album in enumerate(results, 1):
            title = album.get("title", "未知标题")
            if len(title) > 50:
                title = title[:47] + "..."

            album_id = album.get("id", "N/A")

            lines.append(f"{i}. 【{album_id}】{title}")

            if album.get("tags"):
                tags = album["tags"][:3]
                lines.append(f"   🏷️ {', '.join(tags)}")

            lines.append("")

        lines.append("━━━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 使用 /jmi <ID> 查看详情")
        lines.append("💡 使用 /jm <ID> 直接下载")
        lines.append(f"💡 使用 /jms {keyword} {page + 1} 查看下一页")
        lines.append("💡 可加前缀指定类型: tag: / author: / actor:")

        return "\n".join(lines)

    @classmethod
    def format_ranking_results(
        cls,
        results: list[dict],
        ranking_type: str,
        page: int = 1,
        category: str = "all",
    ) -> str:
        """
        格式化排行榜结果

        Args:
            results: 排行榜结果列表
            ranking_type: 排行榜类型 (day/week/month)
            page: 当前页码
            category: 分类类型

        Returns:
            格式化后的字符串
        """
        if not results:
            return "🏆 暂无排行榜数据"

        type_names = {"day": "日", "week": "周", "month": "月"}
        type_name = type_names.get(ranking_type, "周")
        cat_name = cls.CATEGORY_NAMES.get(category, category)
        title_cat = "" if category == "all" else f"{cat_name} · "
        lines = [
            f"🏆 {title_cat}{type_name}排行榜 (第{page}页)",
            "━━━━━━━━━━━━━━━━━━━━━",
        ]

        for i, album in enumerate(results, 1):
            title = album.get("title", "未知标题")
            if len(title) > 30:
                title = title[:27] + "..."

            album_id = album.get("id", "N/A")

            # 前三名使用特殊emoji
            rank_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
            lines.append(f"{rank_emoji} 【{album_id}】{title}")

        cat_arg = "" if category == "all" else f" {category}"
        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 使用 /jmi <ID> 查看详情")
        lines.append("💡 使用 /jm <ID> 直接下载")
        lines.append(f"💡 使用 /jmrank {ranking_type}{cat_arg} {page + 1} 查看下一页")
        lines.append("")
        lines.append("📊 类型: day(日榜) · week(周榜) · month(月榜)")
        lines.append("📂 可加分类: hanman·doujin·single·short·meiman·3d·cosplay")

        return "\n".join(lines)

    # 常量映射已移至 core/constants.py，这里保留引用以保持兼容性
    CATEGORY_NAMES = CATEGORY_NAMES
    ORDER_NAMES = ORDER_NAMES
    TIME_NAMES = TIME_NAMES

    @classmethod
    def format_recommend_results(
        cls,
        results: list[dict],
        category: str = "all",
        order_by: str = "hot",
        time_range: str = "week",
        page: int = 1,
    ) -> str:
        """
        格式化推荐/分类浏览结果

        Args:
            results: 结果列表
            category: 分类类型
            order_by: 排序方式
            time_range: 时间范围
            page: 当前页码

        Returns:
            格式化后的字符串
        """
        # 获取显示名称
        cat_name = cls.CATEGORY_NAMES.get(category.lower(), category)
        order_name = cls.ORDER_NAMES.get(order_by.lower(), order_by)
        time_name = cls.TIME_NAMES.get(time_range.lower(), time_range)

        if not results:
            return (
                f"📭 暂无推荐内容\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔍 查询: {cat_name} · {time_name}{order_name}\n"
                f"💡 某些分类在特定时间范围内可能没有内容\n"
                f"💡 尝试扩大时间范围，如 week 或 month"
            )

        lines = [
            f"🎯 推荐浏览 - {cat_name} · {time_name}{order_name}",
            f"📄 第 {page} 页",
            "━━━━━━━━━━━━━━━━━━━━━",
        ]

        for i, album in enumerate(results, 1):
            title = album.get("title", "未知标题")
            if len(title) > 30:
                title = title[:27] + "..."

            album_id = album.get("id", "N/A")
            lines.append(f"{i}. 【{album_id}】{title}")

        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 使用 /jmi <ID> 查看详情")
        lines.append("💡 使用 /jm <ID> 直接下载")
        lines.append(f"💡 使用 /jmrec ... {page + 1} 查看下一页")
        lines.append("")
        lines.append("📂 分类: all·doujin·single·short·hanman·meiman·3d·cosplay")
        lines.append("📊 排序: hot(热门)·new(最新)·pic(图多)·like(点赞)")
        lines.append("⏰ 时间: day(今日)·week(本周)·month(本月)·all(全部)")

        return "\n".join(lines)

    @staticmethod
    def format_recommend_help() -> str:
        """
        格式化推荐功能帮助信息

        Returns:
            帮助信息字符串
        """
        return """🎯 推荐浏览使用帮助

【命令格式】
/jmrec [分类] [排序] [时间] [页码]

【分类选项】
all(全部) doujin(同人) single(单本)
short(短篇) hanman(韩漫) meiman(美漫)
3d(3D) cosplay another(其他)

【排序选项】
hot(热门) new(最新) pic(图多) like(点赞)

【时间选项】
day(今日) week(本周) month(本月) all(全部)

【使用示例】
/jmrec                  → 本周全分类热门
/jmrec hanman           → 本周韩漫热门
/jmrec all hot day      → 今日全分类热门
/jmrec doujin new week  → 本周同人最新
/jmrec 3d hot month 2   → 本月3D热门第2页"""

    @staticmethod
    def format_favorites(albums: list[dict], folders: list[dict], page: int = 1) -> str:
        """
        格式化收藏夹结果

        Args:
            albums: 收藏的本子列表
            folders: 收藏夹列表
            page: 当前页码

        Returns:
            格式化后的字符串
        """
        lines = []
        lines.append("⭐ 我的收藏")
        lines.append(f"📄 第 {page} 页")
        lines.append("━━━━━━━━━━━━━━━━━━━━━")

        if not albums:
            lines.append("📭 收藏夹为空")
        else:
            for i, album in enumerate(albums, 1):
                album_id = album.get("id", "")
                title = album.get("title", "未知")
                lines.append(f"{i}. 【{album_id}】{title}")

        # 显示收藏夹列表（如果有多个）
        if folders and len(folders) > 1:
            lines.append("")
            lines.append("📁 收藏夹列表:")
            for folder in folders:
                folder_id = folder.get("id", "")
                folder_name = folder.get("name", "未知")
                lines.append(f"  • [{folder_id}] {folder_name}")

        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 使用 /jmfav <页码> 翻页")
        lines.append("💡 使用 /jmfav <页码> <收藏夹ID> 查看特定收藏夹")
        lines.append("💡 使用 /jmfav add <本子ID> 收藏本子")

        return "\n".join(lines)

    @staticmethod
    def format_subscriptions(subs: list[dict]) -> str:
        """
        格式化订阅列表

        Args:
            subs: 订阅记录列表（含 album_id/title/last_count）

        Returns:
            格式化后的字符串
        """
        lines = ["🔔 我的订阅", "━━━━━━━━━━━━━━━━━━━━━"]

        if not subs:
            lines.append("📭 暂无订阅")
        else:
            for i, sub in enumerate(subs, 1):
                title = sub.get("title") or "未知"
                if len(title) > 30:
                    title = title[:27] + "..."
                lines.append(f"{i}. 【{sub.get('album_id', '')}】{title}")
                lines.append(f"   已记录章节: {sub.get('last_count', 0)}")

        lines.append("━━━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 /jmsub <ID> 订阅 · /jmunsub <ID> 取消订阅")
        lines.append("💡 /jmupdate <ID> 下载新章节")

        return "\n".join(lines)

    @staticmethod
    def format_download_result(result, pack_result=None) -> str:
        """
        格式化下载结果

        Args:
            result: DownloadResult 实例
            pack_result: PackResult 实例（可选）

        Returns:
            格式化后的字符串
        """
        if not result.success:
            return f"❌ 下载失败\n原因: {result.error_message}"

        lines = [
            "✅ 下载完成！",
            "━━━━━━━━━━━━━━━━━━━━━",
            f"📖 {result.title}",
            f"✍️ 作者: {result.author}",
            f"📚 章节: {result.photo_count}",
            f"🖼️ 图片: {result.image_count}",
        ]

        # 下载完整性提示
        if not getattr(result, "all_success", True):
            failed = getattr(result, "failed_images", 0)
            if failed:
                lines[0] = "⚠️ 下载完成（部分失败）"
                lines.append(f"⚠️ 失败图片/章节: {failed}")
            else:
                lines[0] = "⚠️ 下载完成（可能不完整）"

        if pack_result:
            if pack_result.success:
                format_name = {
                    "zip": "ZIP压缩包",
                    "pdf": "PDF文档",
                    "long_img": "长图",
                    "none": "不打包",
                }.get(pack_result.format, pack_result.format)

                lines.append(f"📦 格式: {format_name}")

                if pack_result.format == "none":
                    # none 表示仅本地保存、不发送文件
                    lines.append(f"📁 已保存到本地（未发送）: {result.save_path}")
                elif pack_result.encrypted:
                    lines.append("🔐 已加密")
            else:
                # 打包失败时提示用户
                lines.append(f"⚠️ 打包失败: {pack_result.error_message or '未知错误'}")

        lines.append("━━━━━━━━━━━━━━━━━━━━━")

        return "\n".join(lines)

    @staticmethod
    def format_download_progress(status: str, current: int, total: int) -> str:
        """
        格式化下载进度

        Args:
            status: 状态描述
            current: 当前进度
            total: 总数

        Returns:
            格式化后的字符串
        """
        if total > 0:
            percent = int((current / total) * 100)
            bar_length = 10
            filled = int(bar_length * current / total)
            bar = "█" * filled + "░" * (bar_length - filled)
            return f"⏳ {status}\n[{bar}] {percent}% ({current}/{total})"
        else:
            return f"⏳ {status}..."

    @staticmethod
    def format_help() -> str:
        """
        格式化帮助信息

        Returns:
            帮助信息字符串
        """
        return """📚 JM-Cosmos II - 漫画下载插件

【基本命令】
/jm <ID>     - 下载指定ID的本子
/jmc <ID> <章节> - 下载指定本子的指定章节
/jms <关键词> [页码] - 搜索漫画（支持 tag:/author:/actor: 前缀）
/jmi <ID>    - 查看本子详情
/jmrank      - 查看排行榜（可加分类，如 week hanman）
/jmrec       - 推荐浏览（分类/排序/时间）
/jmhelp      - 显示此帮助信息

【账号命令】
/jmlogin <用户名> <密码> - 登录JM账号
/jmlogout   - 登出账号
/jmstatus   - 查看登录状态
/jmfav      - 查看我的收藏（需登录）

【订阅命令】
/jmsub <ID>     - 订阅本子更新
/jmunsub <ID>   - 取消订阅
/jmsublist      - 查看订阅列表
/jmupdate <ID>  - 下载新增章节

【使用示例】
/jm 123456       - 下载ID为123456的本子
/jms 标签名 2    - 搜索包含该标签的漫画（第2页）
/jmrank week     - 查看周排行榜
/jmrec hanman    - 浏览韩漫热门
/jmrec help      - 查看推荐功能详细帮助
/jmfav 1         - 查看收藏夹第1页

【说明】
• 下载的文件将自动打包发送
• 登录后可访问收藏夹等功能"""

    @staticmethod
    def format_error(error_type: str, detail: str = "") -> str:
        """
        格式化错误信息

        Args:
            error_type: 错误类型
            detail: 详细信息

        Returns:
            格式化后的错误信息
        """
        error_messages = {
            "not_found": "❌ 未找到指定的本子，请检查ID是否正确",
            "network": "❌ 网络连接失败，请稍后重试",
            "permission": "❌ 权限不足，您没有使用此功能的权限",
            "group_disabled": "❌ 此群未启用JM漫画下载功能",
            "invalid_id": "❌ 无效的ID格式，请输入正确的数字ID",
            "download_failed": "❌ 下载失败",
            "pack_failed": "❌ 打包失败",
        }

        msg = error_messages.get(error_type, f"❌ 发生错误: {error_type}")
        if detail:
            msg += f"\n详情: {detail}"
        return msg
