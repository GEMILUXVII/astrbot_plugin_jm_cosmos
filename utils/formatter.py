"""
消息格式化工具
"""


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
            if len(title) > 30:
                title = title[:27] + "..."

            author = album.get("author", "未知")
            album_id = album.get("id", "N/A")

            lines.append(f"{i}. 【{album_id}】{title}")
            lines.append(f"   ✍️ {author}")

            if album.get("tags"):
                tags = album["tags"][:3]
                lines.append(f"   🏷️ {', '.join(tags)}")

            lines.append("")

        lines.append("━━━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 使用 /jmi <ID> 查看详情")
        lines.append("💡 使用 /jm <ID> 直接下载")

        return "\n".join(lines)

    @staticmethod
    def format_ranking_results(
        results: list[dict], ranking_type: str, page: int = 1
    ) -> str:
        """
        格式化排行榜结果

        Args:
            results: 排行榜结果列表
            ranking_type: 排行榜类型 (week/month)
            page: 当前页码

        Returns:
            格式化后的字符串
        """
        if not results:
            return "🏆 暂无排行榜数据"

        type_name = "周" if ranking_type == "week" else "月"
        lines = [
            f"🏆 {type_name}排行榜 (第{page}页)",
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

        lines.append("")
        lines.append("━━━━━━━━━━━━━━━━━━━━━")
        lines.append("💡 使用 /jmi <ID> 查看详情")
        lines.append("💡 使用 /jm <ID> 直接下载")

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

        if pack_result and pack_result.success:
            format_name = {
                "zip": "ZIP压缩包",
                "pdf": "PDF文档",
                "none": "原始文件夹",
            }.get(pack_result.format, pack_result.format)

            lines.append(f"📦 格式: {format_name}")

            if pack_result.encrypted:
                lines.append("🔐 已加密")

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
        return """📚 JM Cosmos2 - 漫画下载插件

【基本命令】
/jm <ID>     - 下载指定ID的本子
/jmc <ID>    - 下载指定ID的章节
/jms <关键词> - 搜索漫画
/jmi <ID>    - 查看本子详情
/jmrank      - 查看排行榜
/jmhelp      - 显示此帮助信息

【账号命令】
/jmlogin <用户名> <密码> - 登录JM账号
/jmlogout   - 登出账号
/jmstatus   - 查看登录状态

【使用示例】
/jm 123456       - 下载ID为123456的本子
/jms 标签名      - 搜索包含该标签的漫画
/jmrank week     - 查看周排行榜
/jmlogin user pw - 登录账号

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
