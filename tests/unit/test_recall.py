"""Message recall delivery tests."""

import importlib
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

class _MessageChain:
    """Minimal message chain used by recall unit tests."""

    def __init__(self, chain):
        self.chain = chain


@pytest.fixture
def recall_module(monkeypatch):
    """Load the recall module with isolated AstrBot component stubs."""
    components_module = types.ModuleType("astrbot.api.message_components")
    components_module.Image = type("Image", (), {})
    components_module.Plain = type("Plain", (), {})
    event_module = types.ModuleType("astrbot.api.event")
    event_module.AstrMessageEvent = object
    event_module.MessageChain = _MessageChain
    monkeypatch.setitem(
        sys.modules, "astrbot.api.message_components", components_module
    )
    monkeypatch.setitem(sys.modules, "astrbot.api.event", event_module)

    plugin_root = Path(__file__).resolve().parents[2]
    utils_package = sys.modules["astrbot_plugin_jm_cosmos.utils"]
    monkeypatch.setattr(utils_package, "__path__", [str(plugin_root / "utils")])
    module_name = "astrbot_plugin_jm_cosmos.utils.recall"
    sys.modules.pop(module_name, None)
    module = importlib.import_module(module_name)
    yield module
    sys.modules.pop(module_name, None)


def test_text_fallback_does_not_retry_files(monkeypatch, recall_module):
    """A file-only chain must not be mistaken for a text fallback."""

    class Plain:
        pass

    class Image:
        pass

    class File:
        pass

    monkeypatch.setattr(recall_module.Comp, "Plain", Plain)
    monkeypatch.setattr(recall_module.Comp, "Image", Image)
    monkeypatch.setattr(recall_module.Comp, "File", File, raising=False)
    monkeypatch.setattr(recall_module, "MessageChain", _MessageChain)

    assert recall_module._get_text_only_chain(_MessageChain([File()])) is None
    plain = Plain()
    assert recall_module._get_text_only_chain(
        _MessageChain([plain, File()])
    ).chain == [plain]


@pytest.mark.asyncio
async def test_send_with_recall_reports_success(monkeypatch, recall_module):
    """A successful OneBot send returns a positive delivery result."""

    class Adapter:
        @staticmethod
        async def _parse_onebot_json(chain):
            return [{"type": "file", "data": {"file": "http://host/file"}}]

    adapter_module = types.ModuleType(
        "astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event"
    )
    adapter_module.AiocqhttpMessageEvent = Adapter
    monkeypatch.setitem(
        sys.modules,
        "astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event",
        adapter_module,
    )

    bot = SimpleNamespace(send_group_msg=AsyncMock(return_value={"message_id": 42}))
    event = SimpleNamespace(
        bot=bot,
        get_platform_name=lambda: "aiocqhttp",
        get_group_id=lambda: "123456",
        get_sender_id=lambda: "654321",
        send=AsyncMock(),
    )

    delivered = await recall_module.send_with_recall(
        event, _MessageChain([object()]), 0
    )

    assert delivered is True
    event.send.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_with_recall_reports_total_failure(monkeypatch, recall_module):
    """The caller can preserve files when both send attempts fail."""

    class Adapter:
        @staticmethod
        async def _parse_onebot_json(chain):
            return [{"type": "file", "data": {"file": "http://host/file"}}]

    adapter_module = types.ModuleType(
        "astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event"
    )
    adapter_module.AiocqhttpMessageEvent = Adapter
    monkeypatch.setitem(
        sys.modules,
        "astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event",
        adapter_module,
    )
    monkeypatch.setattr(
        recall_module, "_get_compressed_message_chain", lambda chain: (None, [])
    )
    monkeypatch.setattr(recall_module, "_get_text_only_chain", lambda chain: None)

    bot = SimpleNamespace(
        send_group_msg=AsyncMock(side_effect=RuntimeError("upload failed"))
    )
    event = SimpleNamespace(
        bot=bot,
        get_platform_name=lambda: "aiocqhttp",
        get_group_id=lambda: "123456",
        get_sender_id=lambda: "654321",
        send=AsyncMock(side_effect=RuntimeError("fallback failed")),
    )

    delivered = await recall_module.send_with_recall(
        event, _MessageChain([object()]), 0
    )

    assert delivered is False
    event.send.assert_awaited_once()
