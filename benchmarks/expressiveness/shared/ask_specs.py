"""agent_spec_kit matcher specs aligned to expressiveness C01–C12."""

from __future__ import annotations

from typing import Any

import agent_spec_kit.match as m

from specimens.messages import meta


def tools_spec(check_id: str) -> Any | None:
    mmeta = meta()
    specs: dict[str, Any] = {
        "C02": m.list(
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
            mode="ordered",
            allow_extras=True,
        ),
        "C03": m.list(
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
            mode="ordered",
            allow_extras=True,
        ),
        "C04": m.list(
            [
                m.tool_call(
                    "run_billing_policy_specialist",
                    result=m.object(
                        {"eligible": True, "amount": m.number(min=0.01, max=500.0)},
                        extra="forbid",
                    ),
                ),
            ],
            mode="ordered",
            allow_extras=True,
        ),
        "C05": m.list(
            [m.tool_call("authenticate_customer"), m.tool_call("get_outage_status")],
            mode="ordered",
            allow_extras=True,
        ),
        "C06": m.list([m.tool_call("apply_bill_credit")], mode="ordered", allow_extras=True),
        "C07": m.list(
            [
                m.tool_call("authenticate_customer"),
                m.tool_call(
                    "get_line_status",
                    args=m.object({"line_id": mmeta["line_id"]}, extra="forbid"),
                ),
            ],
            mode="ordered",
            allow_extras=True,
        ),
        "C08": m.list(
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
            mode="ordered",
            allow_extras=True,
        ),
        "C09": m.list(
            [
                m.tool_call(
                    "run_network_diagnostics_specialist",
                    children=[
                        m.tool_call("pull_network_events"),
                        m.tool_call("score_signal_anomaly"),
                    ],
                ),
            ],
            mode="ordered",
            allow_extras=True,
        ),
        "C10": m.list(
            [m.tool_call("heartbeat_ping"), m.tool_call("get_line_status")],
            mode="unordered",
            allow_extras=True,
        ),
        "C12": m.list(
            [m.tool_call("authenticate_customer"), m.tool_call("create_support_ticket")],
            mode="ordered",
            allow_extras=True,
        ),
    }
    return specs.get(check_id)


def output_spec(check_id: str) -> Any | None:
    if check_id == "C01":
        return m.all_of(
            m.one_of(m.contains("credit"), m.contains("refund")),
            m.one_of(m.contains("$"), m.contains("dollar")),
        )
    return None
