"""Trace parsing helpers for hand-written scenario evaluators (no check semantics)."""

from __future__ import annotations

from typing import Any

from diagnostic_comparison.shared.artifact_io import tools_from_artifact


def tools_from_artifact_dict(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    return tools_from_artifact(artifact)


def tool_names(tools: list[dict[str, Any]]) -> list[str]:
    return [str(t.get("name") or "") for t in tools]


def find_tool(tools: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for t in tools:
        if (t.get("name") or "") == name:
            return t
    return None


def nested_child_names(tool: dict[str, Any]) -> list[str]:
    children = tool.get("children") or []
    return [str(c.get("name") or "") for c in children]


def first_forbidden_index(tools: list[dict[str, Any]], forbidden: str) -> int | None:
    for i, t in enumerate(tools):
        if (t.get("name") or "") == forbidden:
            return i
    return None
