"""agent_spec_kit implementations — matchers aligned to shared.canonical_checks."""

from __future__ import annotations

import sys
from pathlib import Path

_EXPR = Path(__file__).resolve().parents[2]
if str(_EXPR) not in sys.path:
    sys.path.insert(0, str(_EXPR))

from shared.paths import ensure_paths

ensure_paths()

import agent_spec_kit as ek
import agent_spec_kit.match as m

from specimens.messages import meta, msg_c10, msg_c11_turn1, msg_c12_turns
from shared.store_sim import insert_ticket

_TELECOM = _EXPR.parent / "telecom_support"
if str(_TELECOM) not in sys.path:
    sys.path.insert(0, str(_TELECOM))

from tasks.specs import oracles as o  # noqa: E402


@ek.scenario(agent_fixture="agent_c01", tags=("expressiveness", "C01"), timeout_s=60.0)
async def test_c01_output_rubric(s):
    # CHECK_START
    (
        s.user_message("check").assert_output(
            m.all_of(
                m.one_of(m.contains("credit"), m.contains("refund")),
                m.one_of(m.contains("$"), m.contains("dollar")),
            )
        )
    )
    # CHECK_END
    await s.materialise()


@ek.scenario(agent_fixture="agent_c02", tags=("expressiveness", "C02"), timeout_s=60.0)
async def test_c02_object_shape(s):
    # CHECK_START
    (
        s.user_message("check")
        .assert_tool_calls(
            [
                m.tool_call(
                    "run_network_diagnostics_specialist",
                    result=m.object(
                        {
                            "severity": m.one_of("high"),
                            "recommended_action": m.one_of("create_ticket"),
                            "escalation_reason": m.string(min_len=1),
                        },
                        extra="forbid",
                    ),
                ),
            ],
            ordered=True,
            allow_extras=True,
        )
    )
    # CHECK_END
    await s.materialise()


@ek.scenario(agent_fixture="agent_c03", tags=("expressiveness", "C03"), timeout_s=60.0)
async def test_c03_conditional_object(s):
    # CHECK_START
    (
        s.user_message("check")
        .assert_tool_calls(
            [
                m.tool_call(
                    "run_billing_policy_specialist",
                    result=m.object(
                        {
                            "eligible": m.one_of(True, False),
                            "amount": m.optional(m.number(min=0.01)),
                            "currency": m.optional(m.string()),
                        },
                        extra="forbid",
                        rules=[
                            m.require("amount").when(m.field("eligible") == True),
                            m.forbid("amount").when(m.field("eligible") == False),
                        ],
                    ),
                ),
            ],
            ordered=True,
            allow_extras=True,
        )
    )
    # CHECK_END
    await s.materialise()


@ek.scenario(agent_fixture="agent_c04", tags=("expressiveness", "C04"), timeout_s=60.0)
async def test_c04_numeric_regex(s):
    # CHECK_START
    (
        s.user_message("check")
        .assert_tool_calls(
            [
                m.tool_call(
                    "run_billing_policy_specialist",
                    result=m.object(
                        {"eligible": True, "amount": m.number(min=0.01, max=500.0)},
                        extra="forbid",
                    ),
                ),
            ],
            ordered=True,
            allow_extras=True,
        )
    )
    # CHECK_END
    await s.materialise()


@ek.scenario(agent_fixture="agent_c05", tags=("expressiveness", "C05"), timeout_s=60.0)
async def test_c05_ordered_sequence(s):
    # CHECK_START
    (
        s.user_message("check")
        .assert_tool_calls(
            [
                m.tool_call("authenticate_customer"),
                m.tool_call("get_outage_status"),
            ],
            ordered=True,
            allow_extras=True,
        )
    )
    # CHECK_END
    await s.materialise()


@ek.scenario(agent_fixture="agent_c06", tags=("expressiveness", "C06"), timeout_s=60.0)
async def test_c06_forbidden_tools(s):
    # CHECK_START
    (
        s.user_message("check")
        .forbid_tool_calls([m.tool_call("apply_bill_credit")], ordered=True, allow_extras=True)
    )
    # CHECK_END
    await s.materialise()


@ek.scenario(agent_fixture="agent_c07", tags=("expressiveness", "C07"), timeout_s=60.0)
async def test_c07_tool_args(s):
    # CHECK_START
    (
        s.user_message("check")
        .assert_tool_calls(
            [
                m.tool_call("authenticate_customer"),
                m.tool_call(
                    "get_line_status",
                    args=m.object({"line_id": meta()["line_id"]}, extra="forbid"),
                ),
            ],
            ordered=True,
            allow_extras=True,
        )
    )
    # CHECK_END
    await s.materialise()


@ek.scenario(agent_fixture="agent_c08", tags=("expressiveness", "C08"), timeout_s=60.0)
async def test_c08_tool_result(s):
    # CHECK_START
    (
        s.user_message("check")
        .assert_tool_calls(
            [
                m.tool_call(
                    "run_network_diagnostics_specialist",
                    result=m.object(
                        {
                            "severity": m.one_of("medium", "high"),
                            "recommended_action": m.string(min_len=1),
                            "summary": m.string(min_len=10),
                        },
                        extra="forbid",
                    ),
                ),
            ],
            ordered=True,
            allow_extras=True,
        )
    )
    # CHECK_END
    await s.materialise()


@ek.scenario(agent_fixture="agent_c09", tags=("expressiveness", "C09"), timeout_s=60.0)
async def test_c09_nested_tools(s):
    # CHECK_START
    (
        s.user_message("check")
        .assert_tool_calls(
            [
                m.tool_call(
                    "run_network_diagnostics_specialist",
                    children=[
                        m.tool_call("pull_network_events"),
                        m.tool_call("score_signal_anomaly"),
                    ],
                ),
            ],
            ordered=True,
            allow_extras=True,
        )
    )
    # CHECK_END
    await s.materialise()


@ek.scenario(agent_fixture="agent_c10", tags=("expressiveness", "C10"), timeout_s=60.0)
async def test_c10_unordered_siblings(s):
    # CHECK_START
    (
        s.user_message("check")
        .assert_tool_calls(
            [m.tool_call("heartbeat_ping"), m.tool_call("get_line_status")],
            ordered=False,
            allow_extras=True,
        )
    )
    # CHECK_END
    await s.materialise()


@ek.scenario(agent_fixture="agent_c11", tags=("expressiveness", "C11"), timeout_s=60.0)
async def test_c11_db_state(s, store_c11):
    # CHECK_START
    (
        s.user_message("check")
        .action(lambda: insert_ticket(store_c11, line_id=meta()["line_id"]))
        .assert_that(lambda: o.assert_ticket_exists(store_c11))
    )
    # CHECK_END
    await s.materialise()


@ek.scenario(agent_fixture="agent_c12", tags=("expressiveness", "C12"), timeout_s=60.0)
async def test_c12_multi_turn_memory(s, store_c12):
    # CHECK_START
    t1, t2, t3 = msg_c12_turns()
    line_id = meta()["line_id"]
    (
        s.user_message(t1)
        .user_message(t2)
        .user_message(t3)
        .assert_tool_calls(
            [m.tool_call("authenticate_customer"), m.tool_call("create_support_ticket")],
            ordered=True,
            allow_extras=True,
        )
        .action(lambda: insert_ticket(store_c12, line_id=line_id, ticket_id="INC-9046"))
        .assert_that(lambda: o.assert_ticket_for_line(store_c12, line_id))
    )
    # CHECK_END
    await s.materialise()
