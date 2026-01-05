"""
文件名生成器模块 - 简单的密码后缀功能
"""

import time


def generate_album_filename(
    album_id: str,
    password: str = "",
    chapter_idx: int | None = None,
    show_password: bool = False,
) -> str:
    """
    生成下载文件名

    Args:
        album_id: 本子ID
        password: 打包密码
        chapter_idx: 章节序号 (仅章节下载时传入)
        show_password: 是否显示密码提示

    Returns:
        生成的文件名 (不含扩展名)
    """
    timestamp = int(time.time())

    # 基础格式: ID_timestamp 或 ID_chN_timestamp
    if chapter_idx is not None:
        name = f"{album_id}_Ch{chapter_idx}_{timestamp}"
    else:
        name = f"{album_id}_{timestamp}"

    # 可选：添加密码提示
    if show_password and password:
        name += f"#PW{password}"

    return name
