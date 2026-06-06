"""Deterministic tool-call assertion failures for inspecting failure-box Expected lines.

No API keys required. Each scenario uses a fixed canned trace and an intentionally
wrong ``assert_tool_calls`` / ``forbid_tool_calls`` spec.

Run from repo root::

    uv run agent-spec-kit run examples/tool_error_messages/
    uv run agent-spec-kit run examples/tool_error_messages/ --tags fail-name-at-index-1
"""

from __future__ import annotations

import agent_spec_kit as ek
import agent_spec_kit.match as m


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("tool-error-demo", "expected-failure", "fail-name-at-index-0"),
    timeout_s=30.0,
)
async def test_fail_name_at_index_0(s):
    (
        s.user_message("trace:auth-order")
        .assert_tool_calls(
            [
                m.tool_call("send_troubleshooting_step"),
                m.tool_call("order_replacement_sim"),
            ],
            ordered=True,
            allow_extras=False,
        )
    )


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("tool-error-demo", "expected-failure", "fail-name-at-index-1"),
    timeout_s=30.0,
)
async def test_fail_name_at_index_1(s):
    (
        s.user_message("trace:auth-order")
        .assert_tool_calls(
            [
                m.tool_call("authenticate_customer"),
                m.tool_call("get_line_status"),
            ],
            ordered=True,
            allow_extras=False,
        )
    )


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("tool-error-demo", "expected-failure", "fail-list-length"),
    timeout_s=30.0,
)
async def test_fail_list_length(s):
    (
        s.user_message("trace:auth-only")
        .assert_tool_calls(
            [
                m.tool_call("authenticate_customer"),
                m.tool_call("order_replacement_sim"),
            ],
            ordered=True,
            allow_extras=False,
        )
    )


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("tool-error-demo", "expected-failure", "fail-arg-value"),
    timeout_s=30.0,
)
async def test_fail_arg_value(s):
    (
        s.user_message("trace:auth-order")
        .assert_tool_calls(
            [
                m.tool_call("authenticate_customer"),
                m.tool_call(
                    "order_replacement_sim",
                    args={"line_id": "LINE-001", "address_id": "ADDR-9"},
                ),
            ],
            ordered=True,
            allow_extras=False,
        )
    )


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("tool-error-demo", "expected-failure", "fail-extra-arg"),
    timeout_s=30.0,
)
async def test_fail_extra_arg(s):
    (
        s.user_message("trace:order-sim-type")
        .assert_tool_calls(
            [
                m.tool_call(
                    "order_replacement_sim",
                    args=m.object({"line_id": "LINE-002"}, extra="forbid"),
                ),
            ],
            ordered=True,
            allow_extras=False,
        )
    )


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("tool-error-demo", "expected-failure", "fail-missing-arg"),
    timeout_s=30.0,
)
async def test_fail_missing_arg(s):
    (
        s.user_message("trace:order-line-only")
        .assert_tool_calls(
            [
                m.tool_call(
                    "order_replacement_sim",
                    args=m.object({"line_id": "LINE-002", "address_id": "ADDR-9"}, extra="forbid"),
                ),
            ],
            ordered=True,
            allow_extras=False,
        )
    )


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("tool-error-demo", "expected-failure", "fail-nested-child-name"),
    timeout_s=30.0,
)
async def test_fail_nested_child_name(s):
    (
        s.user_message("trace:nested-forensics")
        .assert_tool_calls(
            [
                m.tool_call(
                    "run_forensics_specialist",
                    children=[
                        m.tool_call("pull_logs"),
                        m.tool_call("pull_metrics"),
                    ],
                ),
            ],
            ordered=True,
            allow_extras=False,
        )
    )


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("tool-error-demo", "expected-failure", "fail-nested-arg"),
    timeout_s=30.0,
)
async def test_fail_nested_arg(s):
    (
        s.user_message("trace:nested-forensics")
        .assert_tool_calls(
            [
                m.tool_call(
                    "run_forensics_specialist",
                    children=[
                        m.tool_call("pull_logs"),
                        m.tool_call(
                            "score_anomaly",
                            args=m.object(
                                {
                                    "source": "logs",
                                    "window_minutes": m.number(min=5, max=60, int_only=True),
                                },
                                extra="forbid",
                                rules=[
                                    m.require("window_minutes").when(m.field("source") == "logs"),
                                ],
                            ),
                        ),
                    ],
                ),
            ],
            ordered=True,
            allow_extras=False,
        )
    )


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("tool-error-demo", "expected-failure", "fail-large-spec-truncation"),
    timeout_s=30.0,
)
async def test_fail_large_spec_truncation(s):
    (
        s.user_message("trace:five-tools")
        .assert_tool_calls(
            [
                m.tool_call("authenticate_customer"),
                m.tool_call("get_line_status"),
                m.tool_call("send_troubleshooting_step", args={"step": 1}),
                m.tool_call("send_troubleshooting_step", args={"step": 9}),
                m.tool_call("close_ticket"),
            ],
            ordered=True,
            allow_extras=False,
        )
    )


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("tool-error-demo", "expected-failure", "fail-forbidden-tool"),
    timeout_s=30.0,
)
async def test_fail_forbidden_tool(s):
    s.user_message("trace:with-credit").forbid_tool_calls(
        [m.tool_call("apply_account_credit")],
        ordered=True,
    )
