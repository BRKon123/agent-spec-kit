"""Harness: build pydantic_evals SpanTree from frozen expressiveness traces."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from pydantic_evals.otel.span_tree import SpanNode, SpanTree

_T0 = datetime(2020, 1, 1, tzinfo=timezone.utc)


def trace_to_span_tree(trace: dict[str, Any], *, turn: str | None = None) -> SpanTree:
    if turn == "last":
        turns = trace.get("turns") or []
        tools = (turns[-1].get("tools") or []) if turns else []
    else:
        tools = list(trace.get("tools") or [])

    spans: list[SpanNode] = [
        SpanNode(
            name="agent_run",
            trace_id=1,
            span_id=1,
            parent_span_id=None,
            start_timestamp=_T0,
            end_timestamp=_T0 + timedelta(seconds=60),
            attributes={},
        )
    ]
    for i, tool in enumerate(tools):
        spans.append(
            SpanNode(
                name=str(tool.get("name", "")),
                trace_id=1,
                span_id=100 + i,
                parent_span_id=1,
                start_timestamp=_T0 + timedelta(seconds=i),
                end_timestamp=_T0 + timedelta(seconds=i + 1),
                attributes={"tool.args": str(tool.get("args") or {})},
            )
        )
        for j, child in enumerate(tool.get("children") or []):
            spans.append(
                SpanNode(
                    name=str(child.get("name", "")),
                    trace_id=1,
                    span_id=200 + i * 10 + j,
                    parent_span_id=100 + i,
                    start_timestamp=_T0 + timedelta(seconds=i, milliseconds=100 * (j + 1)),
                    end_timestamp=_T0 + timedelta(seconds=i, milliseconds=100 * (j + 2)),
                    attributes={},
                )
            )
    tree = SpanTree()
    tree.add_spans(spans)
    return tree
