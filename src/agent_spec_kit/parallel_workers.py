"""Resolve CLI ``-n`` worker counts (pytest-style)."""

from __future__ import annotations

import argparse
import os
from typing import Literal

NumWorkersArg = int | Literal["auto", "logical"]


def parse_num_workers(value: str) -> NumWorkersArg:
    lowered = value.strip().lower()
    if lowered in ("auto", "logical"):
        return lowered  # type: ignore[return-value]
    try:
        n = int(value, 10)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid worker count {value!r}: expected a positive integer, 'auto', or 'logical'"
        ) from exc
    if n < 1:
        raise argparse.ArgumentTypeError(f"worker count must be >= 1, got {n}")
    return n


def resolve_num_workers(n: NumWorkersArg) -> int:
    if n == "auto":
        return os.cpu_count() or 1
    if n == "logical":
        return _logical_cpu_count()
    return n


def _logical_cpu_count() -> int:
    try:
        import psutil  # type: ignore[import-untyped]
    except ImportError:
        return os.cpu_count() or 1
    return psutil.cpu_count(logical=True) or os.cpu_count() or 1
