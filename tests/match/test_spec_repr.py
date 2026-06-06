"""Tests for matcher spec string representations."""

from __future__ import annotations

import agent_spec_kit.match as m
from agent_spec_kit.match.api import tool_call
from agent_spec_kit.match.spec_repr import format_matcher, format_spec_at_path, matcher_summary


def test_format_tool_call_literal_name_positional_only() -> None:
    spec = tool_call("order_replacement_sim", args={"line_id": "LINE-001"})
    text = format_matcher(spec)
    assert 'tool_call("order_replacement_sim"' in text or "tool_call('order_replacement_sim'" in text
    assert "name=" not in text


def test_format_nested_tool_call_with_children() -> None:
    spec = tool_call(
        "run_forensics_specialist",
        children=[
            tool_call("pull_logs", args={"window_minutes": 15}),
            tool_call("score_anomaly"),
        ],
    )
    text = format_matcher(spec)
    assert "run_forensics_specialist" in text
    assert "pull_logs" in text
    assert "score_anomaly" in text
    assert "children=" in text


def test_format_object_with_rules_and_contains() -> None:
    spec = m.object(
        {"query": m.contains("latency"), "severity": m.one_of("high", "medium")},
        extra="forbid",
        rules=[m.require("pager_group").when(m.field("severity") == "high")],
    )
    text = format_matcher(spec)
    assert "latency" in text
    assert "one_of" in text
    assert "require" in text


def test_format_spec_at_path_name_index_1() -> None:
    spec = [
        tool_call("authenticate_customer"),
        tool_call("order_replacement_sim", args={"line_id": "LINE-001", "address_id": "ADDR-1"}),
    ]
    text = format_spec_at_path(spec, (1, "name"))
    assert "authenticate_customer" in text
    assert "order_replacement_sim" in text
    assert "line_id" not in text
    assert "address_id" not in text
    assert "name=" not in text


def test_format_spec_at_path_arg_field() -> None:
    spec = [
        tool_call(
            "get_line_status",
            args=m.object({"line_id": "LINE-001", "verbose": True}, extra="forbid"),
        ),
        tool_call("send_troubleshooting_step"),
    ]
    text = format_spec_at_path(spec, (0, "args", "line_id"))
    assert "get_line_status" in text
    assert "LINE-001" in text
    assert "send_troubleshooting_step" in text
    assert "verbose" not in text


def test_format_spec_at_path_extra_arg() -> None:
    spec = [
        tool_call(
            "order_replacement_sim",
            args=m.object({"line_id": "LINE-001"}, extra="forbid"),
        ),
    ]
    text = format_spec_at_path(spec, (0, "args", "sim_type"))
    assert "order_replacement_sim" in text
    assert "line_id" in text


def test_format_spec_at_path_nested_child() -> None:
    spec = [
        tool_call(
            "run_forensics_specialist",
            children=[
                tool_call("pull_logs"),
                tool_call(
                    "score_anomaly",
                    args=m.object(
                        {"source": "logs", "window_minutes": m.number(min=5, max=60, int_only=True)},
                        extra="forbid",
                        rules=[m.require("window_minutes").when(m.field("source") == "logs")],
                    ),
                ),
            ],
        ),
    ]
    text = format_spec_at_path(spec, (0, "children", 1, "args", "window_minutes"))
    assert "run_forensics_specialist" in text
    assert "score_anomaly" in text
    assert "window_minutes" in text
    assert "pull_logs" in text or "..." in text


def test_format_spec_large_list_collapses_around_focus() -> None:
    spec = [tool_call(f"tool_{i}", args={"step": i}) for i in range(5)]
    text = format_spec_at_path(spec, (3, "args", "step"))
    assert "tool_3" in text
    assert "step" in text
    assert len(text) <= 600


def test_matcher_summary_equality_and_tool_call() -> None:
    assert matcher_summary(m.match(42)) == "42"
    assert "authenticate" in matcher_summary(tool_call("authenticate_customer"))


def test_format_regex_and_optional() -> None:
    spec = m.optional(m.regex(r"INC-\d+"))
    text = format_matcher(spec)
    assert "optional" in text
    assert "INC" in text


def test_format_forbidden_spec() -> None:
    from agent_spec_kit.match.spec_repr import format_forbidden_spec

    text = format_forbidden_spec([tool_call("apply_account_credit")])
    assert "must not call" in text
    assert "apply_account_credit" in text
    assert "[[0]" not in text
