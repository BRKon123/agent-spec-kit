"""Console-only formatting for failure panels and Rich event traces."""

from __future__ import annotations

import json
from typing import Any

# Keep terminal payloads effectively untruncated for diagnostic exports/parsing.
CONSOLE_ACTUAL_MAX_LEN = 1_000_000
# Keep event-trace values effectively untruncated too; downstream benchmark exports
# depend on full panel text for diagnostic-quality scoring.
CONSOLE_TRACE_VALUE_MAX_LEN = 1_000_000


def try_parse_json_string(value: str) -> Any | None:
    stripped = value.strip()
    if not stripped or stripped[0] not in "{[":
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return None


def pretty_json_value(value: Any) -> Any:
    """Recursively expand JSON-encoded strings for readable console output."""
    if isinstance(value, str):
        parsed = try_parse_json_string(value)
        if parsed is not None:
            return pretty_json_value(parsed)
        return value
    if isinstance(value, dict):
        return {k: pretty_json_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [pretty_json_value(v) for v in value]
    return value


def _truncate_console_text(text: str, *, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def format_value_for_console(value: Any, *, max_len: int = CONSOLE_TRACE_VALUE_MAX_LEN) -> str:
    """Format a scalar, dict, list, or JSON string for compact console display."""
    if value is None:
        return ""
    if isinstance(value, str):
        parsed = try_parse_json_string(value)
        if parsed is not None:
            text = json.dumps(pretty_json_value(parsed), indent=2, default=str)
        else:
            text = value
    elif isinstance(value, (dict, list)):
        text = json.dumps(pretty_json_value(value), indent=2, default=str)
    else:
        text = str(value)
    return _truncate_console_text(text, max_len=max_len)


def format_actual_for_console(
    actual_min: Any,
    *,
    max_len: int = CONSOLE_ACTUAL_MAX_LEN,
) -> str:
    """Pretty-print ``actual_min`` for failure panels; truncate only for the console."""
    if isinstance(actual_min, (dict, list, tuple)):
        payload = list(actual_min) if isinstance(actual_min, tuple) else actual_min
        body = json.dumps(pretty_json_value(payload), indent=2, default=str)
    elif isinstance(actual_min, str):
        parsed = try_parse_json_string(actual_min)
        if parsed is not None:
            body = json.dumps(pretty_json_value(parsed), indent=2, default=str)
        else:
            body = actual_min
    else:
        body = str(actual_min)
    return _truncate_console_text(body, max_len=max_len)
