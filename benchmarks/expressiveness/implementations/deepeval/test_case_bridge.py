"""Harness: map frozen expressiveness traces to DeepEval LLMTestCase objects."""

from __future__ import annotations

import json
from typing import Any

from deepeval.test_case import LLMTestCase, ToolCall


def tools_from_trace(trace: dict[str, Any], *, turn: str | None = None) -> list[dict[str, Any]]:
    if turn == "last":
        turns = trace.get("turns") or []
        return list((turns[-1].get("tools") or []) if turns else [])
    return list(trace.get("tools") or [])


def tool_calls_from_trace(trace: dict[str, Any], *, turn: str | None = None) -> list[ToolCall]:
    return [
        ToolCall(name=str(t.get("name", "")), input_parameters=dict(t.get("args") or {}))
        for t in tools_from_trace(trace, turn=turn)
    ]


def llm_test_case_for_trace(trace: dict[str, Any], *, turn: str | None = None) -> LLMTestCase:
    return LLMTestCase(
        input="check",
        actual_output=str(trace.get("output", "")),
        tools_called=tool_calls_from_trace(trace, turn=turn),
    )


def specialist_result(trace: dict[str, Any], name: str) -> Any:
    for t in trace.get("tools") or []:
        if t.get("name") == name:
            return t.get("result")
    return None


def specialist_result_json(trace: dict[str, Any], name: str) -> str:
    result = specialist_result(trace, name)
    if result is None:
        return ""
    return json.dumps(result)
