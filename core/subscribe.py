"""
订阅管理模块

基于 SQLite 记录用户对本子的更新订阅，供后台定时检查章节更新使用。
按 (会话, 本子) 维度去重，会话使用 AstrBot 的 unified_msg_origin。
"""

import sqlite3
from pathlib import Path

from astrbot.api import logger


class SubscriptionManager:
    """本子更新订阅管理器 - 基于 SQLite"""

    def __init__(self, db_path: Path):
        """
        初始化订阅管理器

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
                    CREATE TABLE IF NOT EXISTS subscriptions (
                        umo TEXT NOT NULL,
                        album_id TEXT NOT NULL,
                        user_id TEXT,
                        title TEXT,
                        last_count INTEGER DEFAULT 0,
                        PRIMARY KEY (umo, album_id)
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"初始化订阅数据库失败: {e}")

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)

    def add(
        self, umo: str, album_id: str, user_id: str, title: str, last_count: int
    ) -> bool:
        """新增或更新一条订阅"""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO subscriptions (umo, album_id, user_id, title, last_count)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(umo, album_id) DO UPDATE SET
                        user_id = excluded.user_id,
                        title = excluded.title,
                        last_count = excluded.last_count
                    """,
                    (str(umo), str(album_id), str(user_id), title, int(last_count)),
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"添加订阅失败: {e}")
            return False

    def remove(self, umo: str, album_id: str) -> bool:
        """取消一条订阅，返回是否确实删除了记录"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM subscriptions WHERE umo = ? AND album_id = ?",
                    (str(umo), str(album_id)),
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"取消订阅失败: {e}")
            return False

    def exists(self, umo: str, album_id: str) -> bool:
        """判断某会话是否已订阅某本子"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT 1 FROM subscriptions WHERE umo = ? AND album_id = ?",
                    (str(umo), str(album_id)),
                )
                return cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"查询订阅失败: {e}")
            return False

    def get_last_count(self, umo: str, album_id: str) -> int | None:
        """获取某订阅记录的已知章节数，未订阅返回 None"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT last_count FROM subscriptions WHERE umo = ? AND album_id = ?",
                    (str(umo), str(album_id)),
                )
                row = cursor.fetchone()
                return row[0] if row else None
        except Exception as e:
            logger.error(f"查询订阅章节数失败: {e}")
            return None

    def update_count(self, umo: str, album_id: str, count: int) -> None:
        """更新某订阅记录的已知章节数"""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE subscriptions SET last_count = ? WHERE umo = ? AND album_id = ?",
                    (int(count), str(umo), str(album_id)),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"更新订阅章节数失败: {e}")

    def list_for(self, umo: str) -> list[dict]:
        """列出某会话的全部订阅"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT album_id, title, last_count FROM subscriptions WHERE umo = ?",
                    (str(umo),),
                )
                return [
                    {"album_id": row[0], "title": row[1], "last_count": row[2]}
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"列出订阅失败: {e}")
            return []

    def list_all(self) -> list[dict]:
        """列出全部订阅（供后台检查使用）"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT umo, album_id, user_id, title, last_count FROM subscriptions"
                )
                return [
                    {
                        "umo": row[0],
                        "album_id": row[1],
                        "user_id": row[2],
                        "title": row[3],
                        "last_count": row[4],
                    }
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"列出全部订阅失败: {e}")
            return []
