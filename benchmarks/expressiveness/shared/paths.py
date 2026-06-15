"""Path helpers for the expressiveness benchmark."""

from __future__ import annotations

from pathlib import Path

BENCH_ROOT = Path(__file__).resolve().parents[1]
TELECOM_ROOT = BENCH_ROOT.parent / "telecom_support"
TRACES_DIR = BENCH_ROOT / "traces"
IMPLEMENTATIONS_DIR = BENCH_ROOT / "implementations"


def ensure_paths() -> None:
    import sys

    for p in (BENCH_ROOT, TELECOM_ROOT):
        s = str(p)
        if s not in sys.path:
            sys.path.insert(0, s)


def trace_path(check_id: str) -> Path:
    return TRACES_DIR / f"{check_id}.json"
