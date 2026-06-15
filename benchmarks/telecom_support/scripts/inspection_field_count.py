#!/usr/bin/env python3
"""
Count inspectable leaf fields at the failure site (nested JSON objects).

Used for manual × ask classification: agent_spec_kit baseline units per fault slot,
then ported frameworks on the same slot. Ratio = ceil(ported / ask).
"""

from __future__ import annotations

import ast
import json
import re
from typing import Any

_PATH_LEAF = re.compile(r"\$\[\d+\]\.(?:args|result|children)\.(\w+)")
_PATH_TOOL = re.compile(r"^\$\[\d+\](?:\.children)?$")
_KEYS_LIST = re.compile(r"keys=\[([^\]]+)\]")
_EXPECTED_TOOLS = re.compile(
    r"expected (\d+) tool call\(s\) in order:\s*([^\n]+)",
    re.IGNORECASE,
)
_FORBIDDEN_IDX = re.compile(
    r"forbidden tool (\w+) at index (\d+)",
    re.IGNORECASE,
)
_FIRST_TOOL = re.compile(
    r"expected first tool (\w+), got '(\w+)'",
    re.IGNORECASE,
)
_FAILED_CRITERIA = re.compile(r"Failed criteria:", re.IGNORECASE)
_PRIVACY_TOOLS = re.compile(
    r"get_customer_profile|get_plan_details|get_line_status",
)


def count_json_leaves(value: Any) -> int:
    """Count leaf fields in a JSON-like value (each scalar = 1)."""
    if value is None:
        return 1
    if isinstance(value, dict):
        if not value:
            return 1
        return sum(count_json_leaves(v) for v in value.values())
    if isinstance(value, list):
        if not value:
            return 1
        return sum(count_json_leaves(item) for item in value)
    return 1


def _parse_json_blob(text: str) -> Any | None:
    text = (text or "").strip()
    if not text:
        return None
    for loader in (json.loads, ast.literal_eval):
        try:
            return loader(text)
        except (json.JSONDecodeError, SyntaxError, ValueError):
            continue
    return None


def _parse_tool_list(actual: str) -> list[dict[str, Any]]:
    data = _parse_json_blob(actual.strip())
    if isinstance(data, list):
        return [t for t in data if isinstance(t, dict)]
    return []


def _tool_at_index(actual: str, index: int) -> dict[str, Any] | None:
    tools = _parse_tool_list(actual)
    if 0 <= index < len(tools):
        return tools[index]
    return None


def _specialist_children(actual: str, tool_index: int = 1) -> list[dict[str, Any]]:
    tool = _tool_at_index(actual, tool_index)
    if not tool:
        return []
    children = tool.get("children")
    if isinstance(children, list):
        return [c for c in children if isinstance(c, dict)]
    return []


def count_ask_units(witness: dict[str, Any]) -> int:
    """Fields the agent_spec_kit panel narrows the developer to."""
    path = (witness.get("path") or "").strip()
    check = witness.get("check") or ""
    expected = witness.get("expected") or ""
    panel = witness.get("panel_text") or ""

    if _PATH_LEAF.search(path):
        return 1

    if _PATH_TOOL.match(path):
        m = re.match(r"^\$\[(\d+)\]", path)
        idx = int(m.group(1)) if m else 0
        if path.endswith(".children"):
            em = _EXPECTED_TOOLS.search(expected) or _EXPECTED_TOOLS.search(panel)
            if em:
                names = [n.strip() for n in em.group(2).split(",") if n.strip()]
                return max(1, len(names))
            children = _specialist_children(witness.get("actual") or "", idx)
            if children:
                return sum(1 + count_json_leaves(c.get("args")) for c in children[:2])
            return 2
        return 1

    if check == "assert_output":
        if _FAILED_CRITERIA.search(panel) or _FAILED_CRITERIA.search(
            witness.get("actual") or ""
        ):
            block = panel or witness.get("actual") or ""
            n = len(re.findall(r"^\s*-\s*\[\d+\]\s+criterion:", block, re.MULTILINE))
            return max(1, n)
        return 1

    if check == "assert_that":
        if _PRIVACY_TOOLS.search(expected):
            return 3
        return 1

    return 1


def count_ported_units(
    failure_box: str,
    witness: dict[str, Any] | None,
) -> int:
    """Fields a developer must inspect given the ported failure message (+ witness structure)."""
    box = (failure_box or "").strip()
    witness = witness or {}

    keys_n = _KEYS_LIST.search(box)
    if keys_n:
        parts = [p.strip().strip("'\"") for p in keys_n.group(1).split(",")]
        return max(1, len([p for p in parts if p]))

    m = _FIRST_TOOL.search(box)
    if m:
        return 2

    m = _FORBIDDEN_IDX.search(box)
    if m:
        _tool, idx_s = m.group(1), int(m.group(2))
        tool = _tool_at_index(witness.get("actual") or "", idx_s)
        if tool:
            return count_json_leaves(tool)
        return 1

    if re.search(r"must not include \w+ key", box, re.I):
        return 1

    if re.search(r"missing .+ tool call", box, re.I):
        tools = _parse_tool_list(witness.get("actual") or "")
        if tools:
            return sum(count_json_leaves(t) for t in tools)
        return 1

    if _PRIVACY_TOOLS.search(box):
        return 3

    if _FAILED_CRITERIA.search(box):
        n = len(re.findall(r"^\s*-\s*\[\d+\]\s+criterion:", box, re.MULTILINE))
        return max(1, n)

    if box.startswith("AssertionError:") or box.startswith("{'key'"):
        exp = witness.get("expected") or ""
        if _PRIVACY_TOOLS.search(exp):
            return 3
        em = _EXPECTED_TOOLS.search(exp) or _EXPECTED_TOOLS.search(
            witness.get("panel_text") or ""
        )
        if em:
            names = [n.strip() for n in em.group(2).split(",") if n.strip()]
            return max(1, len(names))
        actual = witness.get("actual") or ""
        tools = _parse_tool_list(actual)
        if tools:
            return sum(count_json_leaves(t) for t in tools)
        children = _specialist_children(actual)
        if children:
            return sum(count_json_leaves(c) for c in children)
        return 1

    if re.search(r"assertion returned false", box, re.I):
        return 1

    return 1


# Hand-reviewed overrides after reading each failure box (record_key -> units).
# Empty by default; populated by build_inspection_burden_manual.py review pass.
MANUAL_UNITS_OVERRIDES: dict[str, int] = {}
