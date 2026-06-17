"""
下载配额管理器测试

重点验证原子预留（reserve）在并发下不会超发，以及 refund 回退。
"""

import threading

from core.quota import DownloadQuotaManager


class TestQuotaReserve:
    """配额预留测试"""

    def test_no_limit_always_allows(self, data_dir):
        qm = DownloadQuotaManager(data_dir / "q.db")
        ok, used, total = qm.reserve("u", 0)
        assert ok is True
        assert total == 0

    def test_respects_limit_sequential(self, data_dir):
        qm = DownloadQuotaManager(data_dir / "q.db")
        outcomes = [qm.reserve("u", 3)[0] for _ in range(5)]
        assert outcomes == [True, True, True, False, False]

    def test_atomic_under_concurrency(self, data_dir):
        """并发预留时，成功次数必须恰好等于上限，不能超发"""
        qm = DownloadQuotaManager(data_dir / "q.db")
        limit = 5
        worker_count = 30
        barrier = threading.Barrier(worker_count)
        successes = []
        lock = threading.Lock()

        def worker():
            barrier.wait()  # 尽量让所有线程同时冲击
            ok, _, _ = qm.reserve("user", limit)
            if ok:
                with lock:
                    successes.append(1)

        threads = [threading.Thread(target=worker) for _ in range(worker_count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(successes) == limit
        assert qm.get_used_count("user") == limit


class TestQuotaRefund:
    """配额返还测试"""

    def test_refund_restores_slot(self, data_dir):
        qm = DownloadQuotaManager(data_dir / "q.db")
        assert qm.reserve("u", 1)[0] is True
        assert qm.reserve("u", 1)[0] is False  # 已用尽
        qm.refund("u")
        assert qm.reserve("u", 1)[0] is True  # 槽位被返还

    def test_refund_not_below_zero(self, data_dir):
        qm = DownloadQuotaManager(data_dir / "q.db")
        qm.refund("u")  # 尚未预留也不应报错或变负
        assert qm.get_used_count("u") == 0
