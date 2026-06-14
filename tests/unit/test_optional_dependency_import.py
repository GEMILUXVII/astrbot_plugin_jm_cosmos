"""
Optional dependency import tests.
"""

import subprocess
import sys
import textwrap
from pathlib import Path


def test_core_imports_without_jmcomic_dependency():
    """The plugin core package must import before jmcomic is installed."""
    plugin_root = Path(__file__).resolve().parents[2]
    script = textwrap.dedent(
        """
        import builtins
        import importlib.util
        import sys
        import tempfile
        import types
        from pathlib import Path

        real_find_spec = importlib.util.find_spec

        def fake_find_spec(name, *args, **kwargs):
            if name == "jmcomic" or name.startswith("jmcomic."):
                return None
            return real_find_spec(name, *args, **kwargs)

        real_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if level == 0 and (name == "jmcomic" or name.startswith("jmcomic.")):
                raise ModuleNotFoundError("No module named 'jmcomic'")
            return real_import(name, globals, locals, fromlist, level)

        importlib.util.find_spec = fake_find_spec
        builtins.__import__ = fake_import

        logger = types.SimpleNamespace(
            debug=lambda *args, **kwargs: None,
            error=lambda *args, **kwargs: None,
            info=lambda *args, **kwargs: None,
        )
        astrbot = types.ModuleType("astrbot")
        astrbot_api = types.ModuleType("astrbot.api")
        astrbot_api.logger = logger
        sys.modules["astrbot"] = astrbot
        sys.modules["astrbot.api"] = astrbot_api

        import core
        from core.base import JMConfigManager
        from core.browser import JMBrowser
        from core.downloader import JMDownloadManager

        manager = JMConfigManager({}, Path(tempfile.mkdtemp()))
        assert core.JMCOMIC_AVAILABLE is False
        assert manager.get_option() is None
        assert JMDownloadManager(manager).is_available() is False
        assert JMBrowser(manager).is_available() is False
        print("missing_jmcomic_import_ok")
        """
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=plugin_root,
        capture_output=True,
        check=True,
        text=True,
    )

    assert "missing_jmcomic_import_ok" in result.stdout
