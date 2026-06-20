"""
HTTP file server used to expose packed downloads to external protocol adapters.
"""

from __future__ import annotations

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from astrbot.api import logger


class _ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


def _make_handler(directory: Path) -> type[SimpleHTTPRequestHandler]:
    class DownloadRequestHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(directory), **kwargs)

        def list_directory(self, path):  # noqa: ARG002
            self.send_error(403, "Directory listing disabled")
            return None

        def log_message(self, format: str, *args) -> None:
            logger.debug(f"JM-Cosmos HTTP file server: {format % args}")

    return DownloadRequestHandler


class JMHTTPFileServer:
    """Small lifecycle wrapper around a background HTTP file server."""

    def __init__(self) -> None:
        self._server: _ReusableThreadingHTTPServer | None = None
        self._thread: Thread | None = None
        self._directory: Path | None = None

    @property
    def running(self) -> bool:
        return self._server is not None

    @property
    def directory(self) -> Path | None:
        return self._directory

    def start(self, directory: Path, host: str, port: int) -> None:
        self.stop()

        directory = directory.resolve()
        directory.mkdir(parents=True, exist_ok=True)

        handler = _make_handler(directory)
        server = _ReusableThreadingHTTPServer((host, port), handler)
        thread = Thread(
            target=server.serve_forever,
            name="JMCosmosHTTPFileServer",
            daemon=True,
        )
        thread.start()

        self._server = server
        self._thread = thread
        self._directory = directory
        logger.info(f"JM-Cosmos HTTP file server started at {host}:{port}: {directory}")

    def stop(self) -> None:
        server = self._server
        thread = self._thread
        if server is None:
            return

        self._server = None
        self._thread = None
        self._directory = None

        try:
            server.shutdown()
            server.server_close()
            if thread is not None:
                thread.join(timeout=2)
            logger.info("JM-Cosmos HTTP file server stopped")
        except Exception as e:
            logger.warning(f"Failed to stop JM-Cosmos HTTP file server: {e}")
