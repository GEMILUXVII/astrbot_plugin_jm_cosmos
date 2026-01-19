"""
自动撤回工具模块

提供消息发送后自动撤回的功能，仅支持 aiocqhttp 平台。
"""

import asyncio
from pathlib import Path

import astrbot.api.message_components as Comp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, MessageChain


def _compress_image(image_path: str, quality: int = 60) -> str | None:
    """
    压缩图片以减小文件大小

    Args:
        image_path: 原始图片路径
        quality: 压缩质量 (1-100)

    Returns:
        压缩后的图片路径，失败返回 None
    """
    try:
        import time

        from PIL import Image

        path = Path(image_path)
        if not path.exists():
            return None

        # 生成唯一的压缩文件名（使用时间戳避免缓存问题）
        timestamp = int(time.time() * 1000)
        compressed_path = path.parent / f"{path.stem}_compressed_{timestamp}.jpg"

        with Image.open(path) as img:
            # 转换为 RGB（处理 RGBA 等格式）
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # 如果图片太大，先缩小尺寸
            max_size = 1024
            if img.width > max_size or img.height > max_size:
                ratio = min(max_size / img.width, max_size / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # 保存压缩后的图片
            img.save(str(compressed_path), "JPEG", quality=quality, optimize=True)

        logger.debug(
            f"图片已压缩: {path.stat().st_size} -> {compressed_path.stat().st_size} bytes"
        )
        return str(compressed_path)

    except ImportError:
        logger.warning("PIL 未安装，无法压缩图片")
        return None
    except Exception as e:
        logger.warning(f"压缩图片失败: {e}")
        return None


def _get_text_only_chain(message_chain: MessageChain) -> MessageChain | None:
    """
    从消息链中提取纯文字内容（移除图片）

    Returns:
        纯文字消息链，如果没有文字返回 None
    """
    text_components = []

    for comp in message_chain.chain:
        # 跳过图片
        if isinstance(comp, Comp.Image):
            continue
        if isinstance(comp, dict) and comp.get("type") == "image":
            continue
        text_components.append(comp)

    if text_components:
        return MessageChain(text_components)
    return None


def _get_compressed_message_chain(
    message_chain: MessageChain,
) -> tuple[MessageChain | None, list[str]]:
    """
    尝试压缩消息链中的图片

    Returns:
        (压缩后的消息链, 需要清理的临时文件列表)
        如果没有图片或压缩失败返回 (None, [])
    """
    new_chain = []
    has_compressed = False
    temp_files = []

    for comp in message_chain.chain:
        if isinstance(comp, Comp.Image):
            # 获取图片路径
            image_path = getattr(comp, "file", None) or getattr(comp, "path", None)
            if image_path and not str(image_path).startswith(
                ("http://", "https://", "base64://")
            ):
                compressed_path = _compress_image(str(image_path))
                if compressed_path:
                    new_chain.append(Comp.Image(file=compressed_path))
                    temp_files.append(compressed_path)
                    has_compressed = True
                    continue

        new_chain.append(comp)

    if has_compressed:
        return MessageChain(new_chain), temp_files
    return None, []


def _cleanup_temp_files(file_paths: list[str]) -> None:
    """清理临时文件"""
    for path in file_paths:
        try:
            Path(path).unlink(missing_ok=True)
        except Exception:
            pass


async def send_with_recall(
    event: AstrMessageEvent,
    message_chain: MessageChain,
    delay: int = 60,
) -> None:
    """
    发送消息并在指定时间后自动撤回

    Args:
        event: AstrBot消息事件
        message_chain: 要发送的消息链
        delay: 撤回延迟（秒），默认60秒

    Note:
        仅支持 aiocqhttp 平台（QQ/NapCat/Lagrange）
        其他平台会回退到普通发送，不执行撤回
        发送超时时会自动尝试压缩图片后重试
    """
    # 检查平台是否为 aiocqhttp
    if event.get_platform_name() != "aiocqhttp":
        # 其他平台回退到普通发送
        await event.send(message_chain)
        return

    # 导入平台特定的类
    try:
        from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
            AiocqhttpMessageEvent,
        )
    except ImportError:
        # 导入失败时回退到普通发送
        await event.send(message_chain)
        return

    # 获取 bot 实例
    if not hasattr(event, "bot"):
        await event.send(message_chain)
        return

    bot = event.bot
    is_group = bool(event.get_group_id())
    session_id_str = event.get_group_id() if is_group else event.get_sender_id()

    # 确保 session_id 是数字
    if not session_id_str or not str(session_id_str).isdigit():
        await event.send(message_chain)
        return

    session_id = int(session_id_str)

    async def do_send(chain: MessageChain) -> dict | None:
        """执行发送并返回结果"""
        messages = await AiocqhttpMessageEvent._parse_onebot_json(chain)
        if not messages:
            return None

        if is_group:
            return await bot.send_group_msg(group_id=session_id, message=messages)
        else:
            return await bot.send_private_msg(user_id=session_id, message=messages)

    try:
        # 第一次尝试发送
        result = await do_send(message_chain)

        message_id = result.get("message_id") if isinstance(result, dict) else None

        if message_id and delay > 0:
            # 创建后台任务延迟撤回
            asyncio.create_task(_delayed_recall(bot, message_id, delay))
            logger.debug(f"已安排消息 {message_id} 在 {delay} 秒后撤回")

    except Exception as e:
        error_str = str(e)
        is_timeout = "Timeout" in error_str or "timeout" in error_str.lower()
        temp_files = []

        if is_timeout:
            logger.warning(f"发送超时，尝试压缩图片后重试: {e}")

            # 第一次回退：尝试压缩图片
            compressed_chain, temp_files = _get_compressed_message_chain(message_chain)
            if compressed_chain:
                try:
                    result = await do_send(compressed_chain)
                    message_id = (
                        result.get("message_id") if isinstance(result, dict) else None
                    )

                    if message_id and delay > 0:
                        asyncio.create_task(_delayed_recall(bot, message_id, delay))
                        logger.info(
                            f"压缩后发送成功，已安排消息 {message_id} 在 {delay} 秒后撤回"
                        )
                    _cleanup_temp_files(temp_files)
                    return
                except Exception as retry_e:
                    logger.warning(f"压缩后发送仍失败: {retry_e}")
                    _cleanup_temp_files(temp_files)

            # 第二次回退：只发送文字（不带图片）
            text_only_chain = _get_text_only_chain(message_chain)
            if text_only_chain:
                try:
                    result = await do_send(text_only_chain)
                    message_id = (
                        result.get("message_id") if isinstance(result, dict) else None
                    )

                    if message_id and delay > 0:
                        asyncio.create_task(_delayed_recall(bot, message_id, delay))
                    logger.info("图片发送失败，已发送纯文字信息")
                    return
                except Exception as text_e:
                    logger.warning(f"纯文字发送也失败: {text_e}")

        # 最后回退到普通发送
        logger.warning(f"send_with_recall 发送失败，回退到普通发送: {e}")
        try:
            await event.send(message_chain)
        except Exception as fallback_e:
            # 回退发送也失败，记录警告但不中断流程
            logger.warning(f"回退发送也失败，跳过此消息: {fallback_e}")


async def _delayed_recall(bot, message_id: int, delay: int) -> None:
    """
    延迟撤回消息

    Args:
        bot: CQHttp bot实例
        message_id: 消息ID
        delay: 延迟秒数
    """
    await asyncio.sleep(delay)
    try:
        await bot.call_action("delete_msg", message_id=message_id)
        logger.debug(f"已撤回消息 {message_id}")
    except Exception as e:
        # 撤回失败静默处理（消息可能已被手动删除或超时）
        logger.debug(f"撤回消息 {message_id} 失败: {e}")
