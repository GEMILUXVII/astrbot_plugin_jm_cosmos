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

    def reserve(self, user_id: str, limit: int) -> tuple[bool, int, int]:
        """
        原子地预留一次配额：在单个事务内检查并自增，避免并发 TOCTOU。

        Args:
            user_id: 用户 QQ 号
            limit: 每日下载限制次数

        Returns:
            (是否预留成功, 预留后已用次数, 限制次数)
        """
        if limit <= 0:
            return True, 0, 0  # 不限制

        today = self._get_today()
        conn = self._get_connection()
        try:
            conn.isolation_level = None  # 手动管理事务
            conn.execute("BEGIN IMMEDIATE")  # 立即获取写锁，串行化并发预留
            row = conn.execute(
                "SELECT count FROM download_quota WHERE user_id = ? AND date = ?",
                (str(user_id), today),
            ).fetchone()
            used = row[0] if row else 0
            if used >= limit:
                conn.execute("ROLLBACK")
                return False, used, limit
            conn.execute(
                """
                INSERT INTO download_quota (user_id, date, count)
                VALUES (?, ?, 1)
                ON CONFLICT(user_id, date) DO UPDATE SET count = count + 1
                """,
                (str(user_id), today),
            )
            conn.execute("COMMIT")
            return True, used + 1, limit
        except Exception as e:
            # 配额是防滥用的软限制：数据库异常时采取 fail-open（放行本次下载），
            # 以可用性优先。此处显式告警，便于运维察觉降级。
            logger.warning(f"配额预留失败，本次降级为放行 (fail-open): {e}")
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            return True, 0, limit
        finally:
            conn.close()

    def refund(self, user_id: str) -> None:
        """返还一次配额（下载失败时回滚预留），不会低于 0"""
        today = self._get_today()
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    UPDATE download_quota SET count = MAX(0, count - 1)
                    WHERE user_id = ? AND date = ?
                    """,
                    (str(user_id), today),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"返还配额失败: {e}")

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
