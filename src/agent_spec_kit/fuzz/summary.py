"""Deterministic per-trial summary labels (no LLM)."""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from agent_spec_kit.fuzz_config import FuzzConfig


def render_trial_summary(
    *,
    labels: Sequence[str],
    details: Sequence[dict[str, Any]],
    fuzz_config: FuzzConfig,
) -> str:
    """Build a short human-readable line from per-turn behaviour labels."""
    labs = tuple(labels)
    if not labs:
        return "(empty trial)"
    if len(labs) == 1:
        return _one_label(labs[0], fuzz_config)
    # Check for repeated mutation_of(seed[i]) pattern
    if all(l.startswith("mutation_of(seed[") for l in labs) and len(set(labs)) == 1:
        seed_idx = _parse_seed_index(labs[0])
        if seed_idx is not None and 0 <= seed_idx < len(fuzz_config.seed_inputs):
            seed_text = fuzz_config.seed_inputs[seed_idx]
            short = _short(seed_text, 40)
            return f'LLM mutation of "{short}" (×{len(labs)})'
        return f"LLM mutation (×{len(labs)})"
    return " → ".join(_one_label(l, fuzz_config) for l in labs)


def _one_label(label: str, fuzz_config: FuzzConfig) -> str:
    if label.startswith("mutation_of(seed["):
        idx = _parse_seed_index(label)
        if idx is not None and 0 <= idx < len(fuzz_config.seed_inputs):
            return f'llm-mutation("{_short(fuzz_config.seed_inputs[idx], 32)}")'
        return "llm-mutation"
    if ":" in label:
        branch, rest = label.split(":", 1)
        if rest.startswith("mutation_of"):
            return f"{branch}:{_one_label(rest, fuzz_config)}"
    return label


def _parse_seed_index(label: str) -> int | None:
    m = re.match(r"mutation_of\(seed\[(\d+)\]\)", label)
    if not m:
        return None
    return int(m.group(1))


def _short(s: str, max_len: int) -> str:
    s = s.strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 3] + "..."


__all__ = ["render_trial_summary"]
