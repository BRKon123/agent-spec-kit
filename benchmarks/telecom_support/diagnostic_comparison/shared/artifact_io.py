"""Load diagnostic artifacts exported after fault-detection runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ARTIFACT_DIR = Path(__file__).resolve().parents[2] / "tasks" / "fault_detection" / "diagnostic_artifacts"
TRACE_DIR = ARTIFACT_DIR / "traces"
SNAPSHOT_DIR = ARTIFACT_DIR / "snapshots"


def slot_artifact_path(family: str, task: str) -> Path:
    return ARTIFACT_DIR / f"{family}_{task}.json"


def load_artifact(family: str, task: str) -> dict[str, Any] | None:
    path = slot_artifact_path(family, task)
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_tools_for_match(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for t in tools:
        name = t.get("name") or t.get("tool_name") or ""
        children = t.get("children") or []
        norm_children = normalize_tools_for_match(children) if children else []
        entry: dict[str, Any] = {
            "name": name,
            "args": t.get("args") or {},
            "result": t.get("result"),
            "error": t.get("error"),
            "children": norm_children,
            "metadata": t.get("metadata") or {},
        }
        out.append(entry)
    return out


def _json_array_end(raw: str) -> int:
    if not raw.startswith("["):
        return -1
    depth = 0
    for i, ch in enumerate(raw):
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                return i + 1
    return -1


def matcher_error_from_witness_actual(text: str) -> str | None:
    """Return matcher error tail after the tool-call JSON block in a panel Actual field."""
    raw = (text or "").strip()
    if not raw:
        return None
    markers = (
        "could not match",
        "forbidden tool call",
        "unexpected key",
        "extra_key:",
    )
    if not any(m in raw for m in markers):
        return None
    end = _json_array_end(raw)
    if end > 0:
        tail = raw[end:].lstrip("\n")
        if tail.strip():
            return tail.strip()
    for marker in markers:
        if marker in raw:
            return raw[raw.find(marker) :].strip()
    return None


def parse_tools_from_witness_actual(text: str) -> list[dict[str, Any]]:
    """Extract the first JSON tool-call array embedded in a log panel Actual field."""
    raw = (text or "").strip()
    if not raw.startswith("["):
        return []
    end = _json_array_end(raw)
    if end <= 0:
        return []
    try:
        parsed = json.loads(raw[:end])
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return normalize_tools_for_match(parsed)


def tools_from_artifact(artifact: dict[str, Any], *, turn: str = "last") -> list[dict[str, Any]]:
    if turn == "last":
        final = artifact.get("final_tools")
        if final:
            return normalize_tools_for_match(list(final))
        turns = artifact.get("turns") or []
        if turns:
            return normalize_tools_for_match(list(turns[-1].get("tools") or []))
        witness = str(artifact.get("witness_actual") or "")
        if witness:
            parsed = parse_tools_from_witness_actual(witness)
            if parsed:
                return parsed
    return []
