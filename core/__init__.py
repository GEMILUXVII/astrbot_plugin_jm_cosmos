"""
JM-Cosmos II 核心模块

提供下载、浏览、认证、配置、打包、配额等核心功能。
"""
import threading
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
from pathlib import Path
import time

from .auth import JMAuthManager
from .base import JMClientMixin, JMConfigManager
from .browser import JMBrowser
from .downloader import DownloadResult, JMDownloadManager
from .errors import classify_exception
from .jmcomic_loader import is_jmcomic_available
from .packer import JMPacker
from .quota import DownloadQuotaManager
from .subscribe import SubscriptionManager
from astrbot.api import logger

# 集中管理 jmcomic 库的可用性检查
JMCOMIC_AVAILABLE = is_jmcomic_available()
_http_server = None
_http_thread = None


def start_http_server(directory: Path, port: int = 8639, host: str = "0.0.0.0"):
    global _http_server, _http_thread
    """
    启动 HTTP 文件服务，用于给运行在Windows内的napcat提供文件传输
    Args:
        directory: 要共享的目录（Path 对象）
        port: 监听端口
        host: 监听地址
    """
    directory.mkdir(parents=True, exist_ok=True)
    
    class CORSRequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)
    
    # 如果已有服务在运行，先停止
    if _http_server is not None:
        try:
            logger.warning("检测到已有HTTP服务正在运行，正在尝试关闭旧服务...")
            _http_server.shutdown()
            _http_server.server_close()
            _http_server = None
            time.sleep(0.5)  # 等待端口释放
        except Exception as e:
            logger.error(f"关闭已存在的HTTP服务时异常: {e}")
    
    #  自定义 TCPServer 强制设置 SO_REUSEADDR 
    import socket
    class ReuseAddrTCPServer(TCPServer):
        def server_bind(self):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            super().server_bind() 
    
    # 创建新服务
    server = ReuseAddrTCPServer((host, port), CORSRequestHandler)
    _http_server = server

    logger.warning(f"JMComic HTTP服务已开放在： {host}:{port}, serving {directory}")
    
    def serve_forever():
        try:
            server.serve_forever()
        except Exception as e:
            logger.error(f"HTTP服务异常: {e}")
    
    _http_thread = threading.Thread(target=serve_forever, daemon=False)
    _http_thread.start()
    return server

def stop_http_server():
    """停止 HTTP 服务（用于插件卸载时清理）"""
    global _http_server
    if _http_server is not None:
        try:
            _http_server.shutdown()
            _http_server.server_close()
            _http_server = None
            logger.warning("JMComic HTTP服务已被关闭")
        except Exception as e:
            logger.error(f"关闭HTTP服务时异常: {e}")
    else:
        logger.info("HTTP服务早已被关闭或未开启")

__all__ = [
    "JMCOMIC_AVAILABLE",
    "DownloadQuotaManager",
    "JMAuthManager",
    "JMBrowser",
    "JMClientMixin",
    "JMConfigManager",
    "JMDownloadManager",
    "DownloadResult",
    "JMPacker",
    "SubscriptionManager",
    "classify_exception",
]
