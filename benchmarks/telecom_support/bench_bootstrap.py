"""Add TelcoSupportBench-Lite root to sys.path (call before local imports)."""

from __future__ import annotations

import sys
from pathlib import Path


def bench_root(start: Path | None = None) -> Path:
    """Return benchmark root (directory containing ``policy.md``)."""
    here = (start or Path(__file__)).resolve()
    for parent in [here, *here.parents]:
        if (parent / "policy.md").is_file():
            return parent
    raise RuntimeError(f"could not locate telecom_support root from {here}")


def ensure_path(*, start: Path | None = None) -> Path:
    root = bench_root(start)
    s = str(root)
    if s not in sys.path:
        sys.path.insert(0, s)
    return root
