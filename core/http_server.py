"""Token-protected HTTP delivery for packed downloads."""

from __future__ import annotations

from dataclasses import dataclass
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from secrets import token_urlsafe
from threading import Event, Lock, Thread
from time import monotonic
from urllib.parse import urlsplit

from astrbot.api import logger


class _ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


@dataclass
class _RegisteredFile:
    """State associated with one temporary download token."""

    path: Path
    expires_at: float
    served: Event


def _make_handler(
    resolve_token,
    mark_served,
) -> type[SimpleHTTPRequestHandler]:
    """Build a request handler backed by the registered-file resolver.

    Args:
        resolve_token: Callable that resolves a random token to an allowed file.
        mark_served: Callable that records a completed GET response.

    Returns:
        A request handler class restricted to registered files.
    """

    class DownloadRequestHandler(SimpleHTTPRequestHandler):
        _resolved_file: Path | None = None

        def _request_token(self) -> str | None:
            """Extract a token from a ``/files/<token>`` request path.

            Returns:
                The requested token, or ``None`` for an invalid route.
            """
            parts = [part for part in urlsplit(self.path).path.split("/") if part]
            if len(parts) != 2 or parts[0] != "files":
                return None
            return parts[1]

        def send_head(self):
            """Validate the token before opening the registered file.

            Returns:
                The opened file object for GET requests, or ``None`` on failure.
            """
            token = self._request_token()
            file_path = resolve_token(token) if token else None
            if file_path is None:
                self.send_error(404, "File not found")
                return None

            self._resolved_file = file_path
            try:
                return super().send_head()
            finally:
                self._resolved_file = None

        def copyfile(self, source, outputfile) -> None:
            """Copy a validated file and record a completed transfer.

            Args:
                source: Open source file object.
                outputfile: Client response stream.
            """
            super().copyfile(source, outputfile)
            token = self._request_token()
            if token:
                mark_served(token)

        def translate_path(self, path: str) -> str:  # noqa: ARG002
            """Return only the path selected by token validation.

            Args:
                path: Original request path, ignored after token validation.

            Returns:
                The registered local file path.
            """
            return str(self._resolved_file or "")

        def list_directory(self, path):  # noqa: ARG002
            """Reject directory requests.

            Args:
                path: Requested directory path.

            Returns:
                Always ``None`` after sending a forbidden response.
            """
            self.send_error(403, "Directory listing disabled")
            return None

        def log_message(self, format: str, *args) -> None:
            """Forward HTTP access logs to the plugin debug logger.

            Args:
                format: HTTP server log format string.
                *args: Values interpolated into the format string.
            """
            logger.debug(f"JM-Cosmos HTTP file server: {format % args}")

    return DownloadRequestHandler


class JMHTTPFileServer:
    """Serve explicitly registered files through unguessable temporary tokens."""

    def __init__(self) -> None:
        self._server: _ReusableThreadingHTTPServer | None = None
        self._thread: Thread | None = None
        self._directory: Path | None = None
        self._registered_files: dict[str, _RegisteredFile] = {}
        self._lock = Lock()

    @property
    def running(self) -> bool:
        """Return whether the HTTP server is active."""
        with self._lock:
            return self._server is not None

    @property
    def directory(self) -> Path | None:
        """Return the directory that bounds registered files."""
        with self._lock:
            return self._directory

    def start(self, directory: Path, host: str, port: int) -> None:
        """Start the background HTTP server.

        Args:
            directory: Root directory containing files that may be registered.
            host: Address on which the server listens.
            port: TCP port on which the server listens.

        Raises:
            OSError: If the server cannot bind to the requested address.
        """
        self.stop()

        directory = directory.resolve()
        directory.mkdir(parents=True, exist_ok=True)

        handler = _make_handler(
            self._resolve_registered_file,
            self._mark_file_served,
        )
        server = _ReusableThreadingHTTPServer((host, port), handler)
        thread = Thread(
            target=server.serve_forever,
            name="JMCosmosHTTPFileServer",
            daemon=True,
        )

        with self._lock:
            self._server = server
            self._thread = thread
            self._directory = directory
            self._registered_files.clear()

        try:
            thread.start()
        except Exception:
            with self._lock:
                self._server = None
                self._thread = None
                self._directory = None
            server.server_close()
            raise

        logger.info(f"JM-Cosmos HTTP file server started at {host}:{port}: {directory}")

    def register_file(self, file_path: Path, ttl: float = 300) -> str:
        """Register one file and return an unguessable access token.

        Args:
            file_path: Existing file located under the configured server directory.
            ttl: Number of seconds before the token expires.

        Returns:
            A random token accepted by the HTTP request handler.

        Raises:
            RuntimeError: If the HTTP server is not running.
            ValueError: If the path is invalid or ``ttl`` is not positive.
        """
        if ttl <= 0:
            raise ValueError("HTTP file token TTL must be positive")
        resolved_path = file_path.resolve()
        with self._lock:
            directory = self._directory
            if self._server is None or directory is None:
                raise RuntimeError("HTTP file server is not running")

            try:
                resolved_path.relative_to(directory)
            except ValueError as exc:
                raise ValueError("File is outside the HTTP server directory") from exc
            if not resolved_path.is_file():
                raise ValueError("Registered path must be an existing file")

            now = monotonic()
            expired_tokens = [
                token
                for token, registered in self._registered_files.items()
                if registered.expires_at <= now
            ]
            for expired_token in expired_tokens:
                self._registered_files.pop(expired_token, None)

            token = token_urlsafe(32)
            self._registered_files[token] = _RegisteredFile(
                path=resolved_path,
                expires_at=now + ttl,
                served=Event(),
            )
            return token

    def revoke_file(self, token: str | None) -> None:
        """Revoke a previously registered file token.

        Args:
            token: Token returned by :meth:`register_file`.
        """
        if not token:
            return
        with self._lock:
            self._registered_files.pop(token, None)

    def wait_until_served(self, token: str, timeout: float) -> bool:
        """Wait for a registered file GET to finish.

        Args:
            token: Token returned by :meth:`register_file`.
            timeout: Maximum number of seconds to wait.

        Returns:
            Whether the HTTP response completed before the timeout.
        """
        with self._lock:
            registered = self._registered_files.get(token)
        if registered is None:
            return False
        return registered.served.wait(timeout)

    def _resolve_registered_file(self, token: str) -> Path | None:
        """Resolve a token to a still-existing registered file.

        Args:
            token: Token extracted from an HTTP request.

        Returns:
            The registered file path, or ``None`` when unavailable.
        """
        with self._lock:
            registered = self._registered_files.get(token)
            if registered is not None and registered.expires_at <= monotonic():
                self._registered_files.pop(token, None)
                registered = None
        if registered is None or not registered.path.is_file():
            return None
        return registered.path

    def _mark_file_served(self, token: str) -> None:
        """Record a completed HTTP GET for a token.

        Args:
            token: Token extracted from the completed request.
        """
        with self._lock:
            registered = self._registered_files.get(token)
        if registered is not None:
            registered.served.set()

    def stop(self) -> None:
        """Stop the server and revoke all registered file tokens."""
        with self._lock:
            server = self._server
            thread = self._thread
            self._server = None
            self._thread = None
            self._directory = None
            self._registered_files.clear()

        if server is None:
            return

        try:
            server.shutdown()
        except Exception as exc:
            logger.warning(f"Failed to shut down JM-Cosmos HTTP file server: {exc}")
        finally:
            server.server_close()
            if thread is not None:
                thread.join(timeout=2)
        logger.info("JM-Cosmos HTTP file server stopped")
