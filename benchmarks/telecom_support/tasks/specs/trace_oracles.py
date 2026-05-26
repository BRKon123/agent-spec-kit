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
ORDER_SIM_FORBIDDEN = [m.tool_call("order_replacement_sim")]


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


def clarification_output(*criteria: str, threshold: int | None = None):
    """LLM rubric: agent should clarify before acting on ambiguous requests."""
    crit = list(criteria)
    th = threshold if threshold is not None else max(1, len(crit))
    return m.llm_criteria(criteria=crit, threshold=th, model="openai:gpt-5-nano")


def premature_action_output(*line_tokens: str, action: str = "order"):
    """Output must not confirm a premature SIM order or ticket on the wrong line."""
    crit = [
        f"Does not confirm that a replacement SIM {action} was submitted or completed",
        "Does not state that a support ticket was opened before the customer corrected the line",
    ]
    for token in line_tokens:
        if token:
            crit.append(
                f"Does not confirm service actions were taken specifically for line {token!r}"
            )
    parts: list[Any] = [m.llm_criteria(criteria=crit, threshold=len(crit), model="openai:gpt-5-nano")]
    for token in line_tokens:
        if token:
            parts.append(m.not_(m.contains(token)))
    return m.all_of(*parts)


def mutation_claim_output(*required_phrases: str):
    """Customer-facing reply should acknowledge the requested mutation."""
    crit = list(required_phrases) or [
        "Confirms that a support ticket was opened or references a ticket id",
    ]
    return m.llm_criteria(
        criteria=crit,
        threshold=max(1, len(crit)),
        model="openai:gpt-5-nano",
    )


def audit_documentation_output():
    """Reply should mention audit trail or documentation when describing sensitive actions."""
    return m.llm_criteria(
        criteria=[
            "Mentions audit trail, documentation, or record-keeping when describing what was done",
        ],
        threshold=1,
        model="openai:gpt-5-nano",
    )


def issue_binding_output(*topic_criteria: str):
    """Reply topic should match the customer's stated issue after clarification."""
    crit = list(topic_criteria)
    return m.llm_criteria(
        criteria=crit,
        threshold=max(1, len(crit)),
        model="openai:gpt-5-nano",
    )


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
