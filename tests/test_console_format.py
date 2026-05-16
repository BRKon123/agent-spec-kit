"""Console-only formatting helpers."""

from __future__ import annotations

from agent_spec_kit.console_format import (
    CONSOLE_ACTUAL_MAX_LEN,
    format_actual_for_console,
    format_value_for_console,
    pretty_json_value,
)


def test_pretty_json_value_expands_result_strings() -> None:
    actual = [
        {
            "name": "open_incident",
            "result": '{"opened": true, "ticket_id": "INC-1"}',
            "children": [],
        }
    ]
    pretty = pretty_json_value(actual)
    assert pretty[0]["result"] == {"opened": True, "ticket_id": "INC-1"}


def test_format_actual_for_console_indents_json() -> None:
    actual = [{"name": "t", "result": '{"ok": true}', "children": []}]
    text = format_actual_for_console(actual)
    assert '"ok": true' in text
    assert "'{\"ok\": true}'" not in text


def test_format_actual_for_console_formats_tuple_as_json_list() -> None:
    text = format_actual_for_console(("err one", "err two"))
    assert '"err one"' in text
    assert '"err two"' in text


def test_format_actual_for_console_truncates_only_in_console() -> None:
    huge = {"x": "y" * (CONSOLE_ACTUAL_MAX_LEN + 100)}
    text = format_actual_for_console(huge)
    assert text.endswith("...")
    assert len(text) == CONSOLE_ACTUAL_MAX_LEN


def test_format_value_for_console_pretty_prints_json_string() -> None:
    text = format_value_for_console('{"a": 1, "b": 2}')
    assert '"a": 1' in text
    assert "\n" in text
