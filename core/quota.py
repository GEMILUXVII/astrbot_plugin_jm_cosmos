"""
下载配额管理模块

基于 SQLite 实现每用户每日下载次数限制。
用户标识使用 QQ 号（或其他平台的 user_id）。
"""

import sqlite3
from datetime import date
from pathlib import Path

from astrbot.api import logger


class DownloadQuotaManager:
    """下载配额管理器 - 基于 SQLite"""

    def __init__(self, db_path: Path):
        """
        初始化配额管理器

        Args:
            db_path: SQLite 数据库文件路径
        """
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS download_quota (
                        user_id TEXT NOT NULL,
                        date TEXT NOT NULL,
                        count INTEGER DEFAULT 0,
                        PRIMARY KEY (user_id, date)
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"初始化配额数据库失败: {e}")

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)

    def _get_today(self) -> str:
        """获取今天的日期字符串"""
        return date.today().isoformat()

    def get_used_count(self, user_id: str) -> int:
        """
        获取用户今日已使用次数

        Args:
            user_id: 用户 QQ 号

        Returns:
            今日已使用次数
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT count FROM download_quota WHERE user_id = ? AND date = ?",
                    (str(user_id), self._get_today()),
                )
                row = cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            logger.error(f"查询配额失败: {e}")
            return 0

    def check_quota(self, user_id: str, limit: int) -> tuple[bool, int, int]:
        """
        检查用户是否可以下载

        Args:
            user_id: 用户 QQ 号
            limit: 每日下载限制次数

        Returns:
            (是否可下载, 已用次数, 限制次数)
        """
        if limit <= 0:
            return True, 0, 0  # 限制为 0 表示不限制

        used = self.get_used_count(user_id)
        can_download = used < limit
        return can_download, used, limit

    def consume_quota(self, user_id: str) -> int:
        """
        消耗一次配额

        Args:
            user_id: 用户 QQ 号

        Returns:
            消耗后的已用次数
        """
        try:
            today = self._get_today()
            with self._get_connection() as conn:
                # 使用 UPSERT 语法，原子操作
                conn.execute(
                    """
                    INSERT INTO download_quota (user_id, date, count)
                    VALUES (?, ?, 1)
                    ON CONFLICT(user_id, date) DO UPDATE SET count = count + 1
                    """,
                    (str(user_id), today),
                )
                conn.commit()
            return self.get_used_count(user_id)
        except Exception as e:
            logger.error(f"消耗配额失败: {e}")
            return 0

    def get_remaining(self, user_id: str, limit: int) -> int | None:
        """
        获取剩余次数

        Args:
            user_id: 用户 QQ 号
            limit: 每日下载限制次数

        Returns:
            剩余次数，如果不限制则返回 None
        """
        if limit <= 0:
            return None
        used = self.get_used_count(user_id)
        return max(0, limit - used)

    def cleanup_old_data(self, days: int = 7):
        """
        清理过期数据

        Args:
            days: 保留最近多少天的数据
        """
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "DELETE FROM download_quota WHERE date < date('now', ?)",
                    (f"-{days} days",),
                )
                conn.commit()
                logger.debug(f"已清理 {days} 天前的配额数据")
        except Exception as e:
            logger.error(f"清理配额数据失败: {e}")
