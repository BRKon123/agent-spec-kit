"""Render Counterexample / framework messages as ASCII failure boxes for exports."""

from __future__ import annotations

import json
from typing import Any

from agent_spec_kit.failures import Counterexample

_DEFAULT_WIDTH = 82


def _meaningful_path(path: str | None) -> bool:
    if not path:
        return False
    return path.strip() not in ("$", "()")


def _compact_result(value: Any, *, max_len: int = 48) -> str:
    if isinstance(value, dict):
        parts = [f"{k}={v!r}" for k, v in list(value.items())[:6]]
        text = "{" + ", ".join(parts)
        if len(value) > 6:
            text += ", ..."
        text += "}"
    elif isinstance(value, str):
        text = value if len(value) <= max_len else value[: max_len - 3] + "..."
    else:
        text = repr(value)
    if len(text) > max_len:
        text = text[: max_len - 3] + "..."
    return text


def _compact_tool_line(index: int, tool: dict[str, Any]) -> str:
    name = tool.get("name") or "?"
    args = tool.get("args") or {}
    if isinstance(args, dict) and args:
        arg_s = ", ".join(f"{k}={v!r}" for k, v in args.items())
    else:
        arg_s = ""
    res = _compact_result(tool.get("result"))
    return f"  [{index}] {name}({arg_s}) -> {res}"


def _format_actual_compact(actual: Any) -> list[str]:
    if isinstance(actual, list) and actual and all(isinstance(x, dict) for x in actual):
        if all(x.get("name") for x in actual):
            return [_compact_tool_line(i, x) for i, x in enumerate(actual)]
    if isinstance(actual, str):
        text = actual.replace("\n", " ")
        return [f"  {text[:200]}{'...' if len(text) > 200 else ''}"]
    if actual is None:
        return ["  (none)"]
    try:
        dumped = json.dumps(actual, indent=2, default=str)
    except TypeError:
        dumped = repr(actual)
    lines = ["  " + line for line in dumped.splitlines()]
    if len(lines) > 12:
        lines = lines[:12] + ["  ..."]
    return lines


def _wrap_ascii_box(title: str, body_lines: list[str], *, width: int = _DEFAULT_WIDTH) -> str:
    inner_w = width - 4
    border = "+" + "-" * (width - 2) + "+"
    title_pad = f" {title} "
    if len(title_pad) < width - 2:
        side = (width - 2 - len(title_pad)) // 2
        top = "+" + "-" * side + title_pad + "-" * (width - 2 - side - len(title_pad)) + "+"
    else:
        top = border
    out = [top]
    for line in body_lines:
        for chunk in (line.splitlines() or [""]):
            while len(chunk) > inner_w:
                out.append(f"| {chunk[:inner_w]:<{inner_w}} |")
                chunk = chunk[inner_w:]
            out.append(f"| {chunk:<{inner_w}} |")
    out.append(border)
    return "\n".join(out)


def counterexample_to_ascii_box(cx: Counterexample, *, title: str) -> str:
    """Render a Counterexample in the same compact shape as TelcoSupportBench log boxes."""
    body: list[str] = []
    if cx.check_kind:
        body.append(f"Check: {cx.check_kind}")
    if cx.location_detail:
        body.append(f"Where: {cx.location_detail}")
    elif cx.location:
        body.append(f"Where: {cx.location}")
    if _meaningful_path(cx.path):
        body.append(f"Path: {cx.path}")
    body.append("Expected:")
    for line in cx.expected_summary.splitlines():
        body.append(line)
    body.append("Actual:")
    body.extend(_format_actual_compact(cx.actual_min))
    for note in cx.notes:
        if _note_duplicates_compact_actual(note, cx.actual_min):
            continue
        for line in note.splitlines():
            if line.strip():
                body.append(line)
    return _wrap_ascii_box(f"FAIL {title}", body)


def _note_duplicates_compact_actual(note: str, actual: Any) -> bool:
    """Skip JSON tool-list notes when Actual already shows compact tool lines."""
    stripped = note.strip()
    if not stripped.startswith("["):
        return False
    if isinstance(actual, list) and actual and isinstance(actual[0], dict) and actual[0].get("name"):
        return '"name"' in stripped
    return False


def framework_message_to_ascii_box(
    framework: str,
    check_id: str,
    message: str,
    *,
    grade: str = "",
) -> str:
    """Compact box for non-ask framework ports (pytest, langsmith, etc.)."""
    title = f"{framework} ({check_id})"
    if grade:
        title += f"  grade {grade}"
    body = [line for line in message.splitlines() if line.strip()] or [message]
    return _wrap_ascii_box(title, body)


def counterexample_to_dict(cx: Counterexample) -> dict[str, Any]:
    """Serializable snapshot of the internal object used to render failure boxes."""
    return {
        "headline": cx.headline,
        "check_kind": cx.check_kind,
        "location": cx.location,
        "location_detail": cx.location_detail,
        "path": cx.path,
        "expected_summary": cx.expected_summary,
        "actual_min": cx.actual_min,
        "notes": list(cx.notes),
        "events": cx.events is not None,
    }
