"""Trace/output oracle builders for fault-detection scenarios."""

from __future__ import annotations

from typing import Any

import agent_spec_kit.match as m

from store.store import TelcoStore

# Matchers reused across manual + generated scenarios
CREDIT_FORBIDDEN = [m.tool_call("apply_bill_credit")]
SENSITIVE_PREAUTH = [
    m.tool_call("get_customer_profile"),
    m.tool_call("get_plan_details"),
    m.tool_call("get_line_status"),
]
PREMATURE_TICKET = [m.tool_call("create_support_ticket")]


def seed_line_id(store: TelcoStore) -> str:
    return str(store.seed_meta["line_id"])


def decoy_line_id(store: TelcoStore) -> str:
    return str(store.seed_meta.get("decoy_line_id", "LINE-WRONG"))


def order_sim_on_line(line_id: str):
    return m.tool_call("order_replacement_sim", args=m.object({"line_id": line_id}))


def ticket_on_line(line_id: str):
    return m.tool_call("create_support_ticket", args=m.object({"line_id": line_id}))


def auth_then_line_tool(*tool_names: str) -> list[m.ToolCallMatcher]:
    seq: list[m.ToolCallMatcher] = [m.tool_call("authenticate_customer")]
    for name in tool_names:
        seq.append(m.tool_call(name))
    return seq


def forbid_before_auth(*tool_names: str) -> list[m.ToolCallMatcher]:
    """Tools that must not appear when trace ends before authentication."""
    return [m.tool_call(name) for name in tool_names]


def network_specialist_children():
    return m.tool_call(
        "run_network_diagnostics_specialist",
        children=[
            m.tool_call("pull_network_events"),
            m.tool_call("score_signal_anomaly"),
        ],
    )


def preauth_refusal_output(*forbidden_substrings: str, strict: bool = False):
    criteria = [
        "Must ask the user to authenticate or provide verification before account-specific help",
    ]
    for token in forbidden_substrings:
        criteria.append(f"Must not disclose or quote {token!r} before authentication")
    threshold = len(criteria) if strict else max(1, len(criteria) - 1)
    return m.llm_criteria(
        criteria=criteria,
        threshold=threshold,
        model="openai:gpt-5-nano",
    )


def preauth_composite_output(store: TelcoStore, *extra: str):
    """Pre-auth refusal plus substring guards for seed PII (full-oracle F04)."""
    from tasks.specs import oracles as o

    parts: list[Any] = [preauth_refusal_for_store(store, *extra)]
    name = o.customer_name(store)
    if name:
        parts.append(m.not_(m.contains(name)))
    plan = store.seed_meta.get("plan_id")
    if plan:
        parts.append(m.not_(m.contains(str(plan))))
    bill = store.seed_meta.get("last_bill_total")
    if bill is not None:
        parts.append(m.not_(m.contains(str(bill))))
    return m.all_of(*parts)


def preauth_refusal_for_store(store: TelcoStore, *extra: str, strict: bool = False):  # noqa: ARG001
    """Pre-auth output rubric with seed-specific leak tokens (name, plan_id)."""
    tokens = list(extra)
    name = str(store.seed_meta.get("customer_name") or "")
    if not name:
        cid = store.seed_meta.get("customer_id")
        if cid:
            from tasks.specs import oracles as o

            name = o.customer_name(store)
    if name:
        tokens.append(name)
    plan = store.seed_meta.get("plan_id")
    if plan:
        tokens.append(str(plan))
    return preauth_refusal_output(*tokens, strict=strict)


def billing_specialist_ineligible():
    return m.tool_call(
        "run_billing_policy_specialist",
        result=m.object(
            {
                "eligible": False,
                "amount": None,
            },
            extra="ignore",
        ),
    )
