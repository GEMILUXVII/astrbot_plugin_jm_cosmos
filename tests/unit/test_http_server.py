"""HTTP file delivery tests."""

import socket
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

from core import http_server as http_server_module
from core.http_server import JMHTTPFileServer


def test_server_only_exposes_registered_tokens(tmp_path: Path):
    """Registered tokens work while direct paths and revoked tokens do not."""
    file_path = tmp_path / "350234 #PWsecret.zip"
    payload = b"token-protected-download"
    file_path.write_bytes(payload)
    server = JMHTTPFileServer()

    try:
        server.start(tmp_path, "127.0.0.1", 0)
        port = server._server.server_address[1]
        token = server.register_file(file_path)
        file_url = f"http://127.0.0.1:{port}/files/{token}"

        head_request = urllib.request.Request(file_url, method="HEAD")
        with urllib.request.urlopen(head_request, timeout=3) as response:
            assert response.status == 200
        assert server.wait_until_served(token, 0) is False

        with urllib.request.urlopen(file_url, timeout=3) as response:
            assert response.read() == payload
        assert server.wait_until_served(token, 1) is True

        with pytest.raises(urllib.error.HTTPError) as direct_request:
            urllib.request.urlopen(
                f"http://127.0.0.1:{port}/{urllib.parse.quote(file_path.name)}",
                timeout=3,
            )
        assert direct_request.value.code == 404

        server.revoke_file(token)
        with pytest.raises(urllib.error.HTTPError) as revoked_request:
            urllib.request.urlopen(file_url, timeout=3)
        assert revoked_request.value.code == 404
    finally:
        server.stop()


def test_server_rejects_files_outside_root(tmp_path: Path):
    """Files outside the configured download directory cannot be registered."""
    download_dir = tmp_path / "downloads"
    download_dir.mkdir()
    outside_file = tmp_path / "outside.zip"
    outside_file.write_bytes(b"outside")
    server = JMHTTPFileServer()

    try:
        server.start(download_dir, "127.0.0.1", 0)
        with pytest.raises(ValueError, match="outside"):
            server.register_file(outside_file)
    finally:
        server.stop()


def test_server_stop_releases_port(tmp_path: Path):
    """Stopping the server closes its listening socket."""
    server = JMHTTPFileServer()
    server.start(tmp_path, "127.0.0.1", 0)
    port = server._server.server_address[1]

    server.stop()

    probe = socket.socket()
    try:
        probe.bind(("127.0.0.1", port))
    finally:
        probe.close()


def test_expired_token_is_rejected(tmp_path: Path, monkeypatch):
    """Unused tokens stop resolving after their bounded lifetime."""
    clock = [100.0]
    monkeypatch.setattr(http_server_module, "monotonic", lambda: clock[0])
    file_path = tmp_path / "output.zip"
    file_path.write_bytes(b"expired")
    server = JMHTTPFileServer()

    try:
        server.start(tmp_path, "127.0.0.1", 0)
        port = server._server.server_address[1]
        token = server.register_file(file_path, ttl=5)
        clock[0] = 106.0

        with pytest.raises(urllib.error.HTTPError) as expired_request:
            urllib.request.urlopen(
                f"http://127.0.0.1:{port}/files/{token}", timeout=3
            )
        assert expired_request.value.code == 404
    finally:
        server.stop()
