"""
自动撤回工具模块

提供消息发送后自动撤回的功能，仅支持 aiocqhttp 平台。
"""

import asyncio

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent, MessageChain


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

    try:
        # 解析消息为 OneBot 格式
        messages = await AiocqhttpMessageEvent._parse_onebot_json(message_chain)

        if not messages:
            return

        # 发送消息并获取 message_id
        if is_group:
            result = await bot.send_group_msg(group_id=session_id, message=messages)
        else:
            result = await bot.send_private_msg(user_id=session_id, message=messages)

        message_id = result.get("message_id") if isinstance(result, dict) else None

        if message_id and delay > 0:
            # 创建后台任务延迟撤回
            asyncio.create_task(_delayed_recall(bot, message_id, delay))
            logger.debug(f"已安排消息 {message_id} 在 {delay} 秒后撤回")

    except Exception as e:
        logger.warning(f"send_with_recall 发送失败，回退到普通发送: {e}")
        await event.send(message_chain)


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
