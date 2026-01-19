"""
tests 根目录配置

注册 pytest markers，供单元测试和集成测试共用。
"""


def pytest_configure(config):
    """注册自定义 markers"""
    config.addinivalue_line("markers", "integration: 集成测试（需要网络连接）")
    config.addinivalue_line("markers", "slow: 慢速测试")
    config.addinivalue_line("markers", "requires_login: 需要登录账号的测试")
