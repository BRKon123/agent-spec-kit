"""Plain-pytest trace assertion helpers (no agent_spec_kit matchers)."""

from __future__ import annotations

from typing import Any


def walk_root_tools(trace: dict[str, Any]) -> list[dict[str, Any]]:
    return list(trace.get("tools") or [])


def tool_names(tools: list[dict[str, Any]]) -> list[str]:
    return [str(t.get("name", "")) for t in tools]


def find_tool(tools: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for t in tools:
        if t.get("name") == name:
            return t
    return None


def ordered_subsequence(expected: list[str], actual: list[str], *, allow_extras: bool) -> bool:
    if not allow_extras and len(actual) != len(expected):
        return False
    ei = 0
    for name in actual:
        if ei < len(expected) and name == expected[ei]:
            ei += 1
    return ei == len(expected)


def unordered_set(expected: list[str], actual: list[str], *, allow_extras: bool) -> bool:
    exp_set = set(expected)
    act_set = set(actual)
    if not allow_extras and len(actual) != len(expected):
        return False
    return exp_set <= act_set


def any_forbidden_present(
    tools: list[dict[str, Any]], forbidden_names: list[str]
) -> str | None:
    names = tool_names(tools)
    for f in forbidden_names:
        if f in names:
            return f
    return None


def nested_children(tool: dict[str, Any]) -> list[dict[str, Any]]:
    return list(tool.get("children") or [])


def dict_has_keys(obj: dict[str, Any], required: set[str], forbidden_extras: bool) -> bool:
    keys = set(obj.keys())
    if not required <= keys:
        return False
    if forbidden_extras and keys - required:
        return False
    return True
