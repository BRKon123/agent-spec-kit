"""Discover and import scenario modules (``test_*.py``, ``fixtures.py``)."""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path


def collect_module_paths(root: Path) -> list[Path]:
    """Single file, or directory: all ``test_*.py`` and ``fixtures.py`` recursively."""
    root = root.expanduser()
    if root.is_file():
        return [root.resolve()]
    base = root.resolve()
    found: set[Path] = set()
    for pattern in ("test_*.py", "fixtures.py"):
        for p in base.rglob(pattern):
            if p.is_file():
                found.add(p.resolve())
    return sorted(found)


def import_path(path: Path) -> None:
    """Import a Python file as a uniquely named module (side effects: decorators register)."""
    path = path.resolve()
    digest = hashlib.sha256(str(path).encode()).hexdigest()[:16]
    unique = f"agent_spec_kit_discovered_{digest}"
    spec = importlib.util.spec_from_file_location(unique, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[unique] = mod
    spec.loader.exec_module(mod)


def import_paths(paths: list[Path]) -> None:
    for p in paths:
        import_path(p)


__all__ = ["collect_module_paths", "import_path", "import_paths"]
