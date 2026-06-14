"""
JMComic optional dependency loader.
"""

import importlib.util
from typing import Any


def is_jmcomic_available() -> bool:
    """Check whether jmcomic can be discovered without importing it."""
    try:
        return importlib.util.find_spec("jmcomic") is not None
    except (ImportError, ValueError):
        return False


def import_jmcomic() -> Any | None:
    """Import jmcomic lazily so plugin startup does not require the dependency."""
    try:
        import jmcomic
    except ImportError:
        return None
    return jmcomic


def can_import_jmcomic() -> bool:
    """Check whether jmcomic can actually be imported at runtime."""
    return import_jmcomic() is not None
