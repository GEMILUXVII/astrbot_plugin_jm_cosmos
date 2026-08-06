"""Packed file delivery tests for the plugin entry point."""

import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, call

import pytest


class _Plain:
    def __init__(self, text: str):
        self.text = text


class _File:
    def __init__(self, name: str, file: str = "", url: str = ""):
        self.name = name
        self.file = file
        self.url = url


class _MessageChain:
    def __init__(self, chain):
        self.chain = chain


@pytest.fixture
def main_module(monkeypatch):
    """Load main.py with minimal AstrBot and plugin dependency stubs."""

    class Filter:
        @staticmethod
        def command(*args, **kwargs):
            return lambda func: func

    class Star:
        def __init__(self, context):
            self.context = context

    class StarTools:
        @staticmethod
        def get_data_dir(name):
            return Path(name)

    class Formatter:
        @staticmethod
        def format_download_result(result, pack_result):
            return "download complete"

    class Packer:
        cleanup = MagicMock()

    components_module = types.ModuleType("astrbot.api.message_components")
    components_module.Plain = _Plain
    components_module.File = _File
    event_module = types.ModuleType("astrbot.api.event")
    event_module.AstrMessageEvent = object
    event_module.MessageChain = _MessageChain
    event_module.filter = Filter()
    star_module = types.ModuleType("astrbot.api.star")
    star_module.Context = object
    star_module.Star = Star
    star_module.StarTools = StarTools
    star_module.register = lambda *args, **kwargs: lambda cls: cls
    monkeypatch.setitem(
        sys.modules, "astrbot.api.message_components", components_module
    )
    monkeypatch.setitem(sys.modules, "astrbot.api.event", event_module)
    monkeypatch.setitem(sys.modules, "astrbot.api.star", star_module)

    api_module = sys.modules["astrbot.api"]
    monkeypatch.setattr(api_module, "AstrBotConfig", object, raising=False)

    core_package = sys.modules["astrbot_plugin_jm_cosmos.core"]
    dependencies = {
        "DownloadQuotaManager": object,
        "JMAuthManager": object,
        "JMBrowser": object,
        "JMConfigManager": object,
        "JMDownloadManager": object,
        "JMHTTPFileServer": object,
        "JMPacker": Packer,
        "SubscriptionManager": object,
        "classify_exception": lambda exc: ("unknown", str(exc)),
    }
    for name, value in dependencies.items():
        monkeypatch.setattr(core_package, name, value, raising=False)

    utils_package = sys.modules["astrbot_plugin_jm_cosmos.utils"]
    monkeypatch.setattr(utils_package, "MessageFormatter", Formatter, raising=False)
    monkeypatch.setattr(
        utils_package,
        "generate_album_filename",
        lambda **kwargs: "output",
        raising=False,
    )
    monkeypatch.setattr(
        utils_package,
        "send_with_recall",
        AsyncMock(return_value=True),
        raising=False,
    )

    plugin_root = Path(__file__).resolve().parents[2]
    module_name = "astrbot_plugin_jm_cosmos.main_delivery_test"
    spec = importlib.util.spec_from_file_location(module_name, plugin_root / "main.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    yield module
    sys.modules.pop(module_name, None)


def _make_delivery_context(
    main_module,
    tmp_path: Path,
    delivery_result: bool = True,
    served: bool = True,
):
    """Build a plugin instance and event for delivery tests.

    Args:
        main_module: Isolated plugin entry module.
        tmp_path: Temporary directory for result paths.
        delivery_result: Result returned by the message delivery helper.
        served: Whether the HTTP server observed a completed GET.

    Returns:
        Plugin, event, download result, pack result, and token revoker.
    """
    plugin = main_module.JMCosmosPlugin.__new__(main_module.JMCosmosPlugin)
    plugin.config_manager = SimpleNamespace(
        auto_recall_enabled=False,
        auto_recall_delay=60,
        auto_delete_after_send=True,
    )
    revoker = MagicMock()
    served_waiter = MagicMock(return_value=served)
    plugin._http_file_server = SimpleNamespace(
        revoke_file=revoker,
        wait_until_served=served_waiter,
    )
    file_component = _File("output.zip", url="http://host/files/token")
    plugin._build_file_component = MagicMock(return_value=(file_component, "token"))
    main_module.send_with_recall = AsyncMock(return_value=delivery_result)
    event = SimpleNamespace(
        plain_result=lambda text: text,
        send=AsyncMock(),
    )
    result = SimpleNamespace(save_path=tmp_path / "source")
    pack_result = SimpleNamespace(
        success=True,
        output_path=tmp_path / "output.zip",
        format="zip",
    )
    return plugin, event, result, pack_result, revoker, served_waiter


@pytest.mark.asyncio
async def test_failed_delivery_preserves_local_files(main_module, tmp_path: Path):
    """An upload failure keeps both source and packed output available."""
    plugin, event, result, pack_result, revoker, served_waiter = (
        _make_delivery_context(main_module, tmp_path, delivery_result=False)
    )
    main_module.JMPacker.cleanup.reset_mock()

    messages = [
        message
        async for message in plugin._emit_packed_file(event, result, pack_result)
    ]

    assert messages[0] == "download complete"
    assert "文件发送失败" in messages[1]
    main_module.JMPacker.cleanup.assert_not_called()
    revoker.assert_called_once_with("token")
    served_waiter.assert_not_called()


@pytest.mark.asyncio
async def test_successful_delivery_cleans_local_files(main_module, tmp_path: Path):
    """Confirmed direct delivery permits automatic cleanup."""
    plugin, event, result, pack_result, revoker, served_waiter = _make_delivery_context(
        main_module, tmp_path
    )
    main_module.JMPacker.cleanup.reset_mock()

    messages = [
        message
        async for message in plugin._emit_packed_file(event, result, pack_result)
    ]

    assert messages == ["download complete"]
    sent_chain = main_module.send_with_recall.await_args.args[1]
    assert sent_chain.chain == [plugin._build_file_component.return_value[0]]
    assert main_module.JMPacker.cleanup.call_args_list == [
        call(result.save_path),
        call(pack_result.output_path),
    ]
    revoker.assert_called_once_with("token")
    served_waiter.assert_called_once_with("token", 30)


@pytest.mark.asyncio
async def test_auto_recall_receives_file_only_chain(main_module, tmp_path: Path):
    """Automatic recall must not mix result text with the file segment."""
    plugin, event, result, pack_result, _, _ = _make_delivery_context(
        main_module, tmp_path
    )
    plugin.config_manager.auto_recall_enabled = True
    plugin.config_manager.auto_delete_after_send = False
    main_module.send_with_recall = AsyncMock(return_value=True)

    messages = [
        message
        async for message in plugin._emit_packed_file(event, result, pack_result)
    ]

    assert messages == ["download complete"]
    file_chain = main_module.send_with_recall.await_args.args[1]
    assert len(file_chain.chain) == 1
    assert isinstance(file_chain.chain[0], _File)
    event.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_unconfirmed_http_fetch_preserves_token_and_files(
    main_module, tmp_path: Path
):
    """A missing HTTP GET leaves the token alive until its bounded expiry."""
    plugin, event, result, pack_result, revoker, served_waiter = (
        _make_delivery_context(main_module, tmp_path, served=False)
    )
    main_module.JMPacker.cleanup.reset_mock()

    messages = [
        message
        async for message in plugin._emit_packed_file(event, result, pack_result)
    ]

    assert "文件发送失败" in messages[1]
    main_module.JMPacker.cleanup.assert_not_called()
    revoker.assert_not_called()
    served_waiter.assert_called_once_with("token", 30)
