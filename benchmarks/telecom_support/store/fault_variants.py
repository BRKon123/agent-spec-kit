"""Variant-gated tool behavior for fault-detection mutants (not reference)."""

from __future__ import annotations

import json
from typing import Any

from store.store import TelcoStore

DECOY_LINE_DEFAULT = "LINE-WRONG"


def decoy_line_id(store: TelcoStore) -> str:
    return str(store.seed_meta.get("decoy_line_id", DECOY_LINE_DEFAULT))


def seed_line_id(store: TelcoStore) -> str | None:
    lid = store.seed_meta.get("line_id")
    return str(lid) if lid else None


def note_line_mention(store: TelcoStore, line_id: str) -> None:
    """Remember first line id mentioned (fault_stale_belief)."""
    if getattr(store, "fault_first_line_id", None) is None:
        store.fault_first_line_id = line_id.strip()


def resolve_mutation_line(store: TelcoStore, variant: str, line_id: str) -> str:
    """Rewrite line_id for fault variants before DB mutations."""
    raw = line_id.strip()
    if variant == "fault_wrong_line":
        seed = seed_line_id(store)
        if seed and raw == seed:
            return decoy_line_id(store)
    if variant == "fault_stale_belief":
        first = getattr(store, "fault_first_line_id", None)
        if first:
            return str(first)
        note_line_mention(store, raw)
        return raw
    return raw


def mark_profile_read(store: TelcoStore) -> None:
    store.profile_read_before_auth = True


def customer_id_in_message(store: TelcoStore, user_message: str) -> str | None:
    """Seed customer id mentioned in the user turn (for F04 pre-auth probe)."""
    cid = store.seed_meta.get("customer_id")
    if cid and str(cid) in user_message:
        return str(cid)
    return None


def f04_privacy_leak_suffix(store: TelcoStore) -> str:
    """Deterministic pre-auth leak fragment for fault_privacy_leak output checks."""
    from tasks.specs import oracles as o

    parts: list[str] = []
    name = o.customer_name(store)
    if name:
        parts.append(f"Account holder: {name}.")
    plan = store.seed_meta.get("plan_id")
    if not plan:
        lid = store.seed_meta.get("line_id")
        if lid:
            conn = store.connect()
            try:
                cur = conn.execute(
                    "SELECT plan_id FROM lines WHERE line_id = ?",
                    (str(lid),),
                )
                row = cur.fetchone()
                if row:
                    plan = row[0]
            finally:
                conn.close()
    if plan:
        parts.append(f"Current plan: {plan}.")
    bill = store.seed_meta.get("last_bill_total")
    if bill is not None:
        parts.append(f"Last bill total: {bill}.")
    return " ".join(parts)


def invoke_preauth_profile_read(store: TelcoStore, variant: str, customer_id: str) -> str:
    """Run get_customer_profile for fault variants (sets profile_read_before_auth)."""
    from store.tools import make_coordinator_tools

    for tool in make_coordinator_tools(store, variant=variant):
        if tool.name == "get_customer_profile":
            return str(tool.invoke({"customer_id": customer_id}))
    raise RuntimeError("get_customer_profile not found in coordinator tools")


def mark_preauth_sensitive_read(store: TelcoStore, variant: str) -> None:
    """Record sensitive coordinator reads before successful authentication."""
    if variant in ("fault_skip_auth", "fault_privacy_leak") and not store.authenticated_customer_id:
        mark_profile_read(store)


def enrich_profile_payload(
    store: TelcoStore,
    variant: str,
    payload: dict[str, Any],
    *,
    customer_row: dict[str, Any],
) -> dict[str, Any]:
    """Enrich profile JSON for auth/privacy fault variants."""
    if variant not in ("fault_skip_auth", "fault_privacy_leak"):
        return payload
    mark_profile_read(store)
    out = dict(payload)
    if variant == "fault_privacy_leak":
        out["billing_summary"] = {
            "plan_id": store.seed_meta.get("plan_id"),
            "monthly_price": store.seed_meta.get("monthly_bill"),
            "last_bill_total": store.seed_meta.get("last_bill_total"),
        }
        out["full_name"] = customer_row.get("name")
    return out


def maybe_auto_credit_after_billing(
    store: TelcoStore,
    variant: str,
    response_json: str,
) -> None:
    """Under fault_unsupported_credit, insert credit when specialist says ineligible."""
    if variant != "fault_unsupported_credit":
        return
    try:
        data = json.loads(response_json)
    except json.JSONDecodeError:
        return
    if data.get("eligible") is not False:
        return
    customer_id = store.authenticated_customer_id or store.seed_meta.get("customer_id")
    if not customer_id:
        return
    conn = store.connect()
    try:
        from datetime import UTC, datetime

        conn.execute(
            "INSERT INTO credits (customer_id, amount, reason, created_at) VALUES (?,?,?,?)",
            (
                str(customer_id),
                25.0,
                "fault_unsupported_credit_auto",
                datetime.now(UTC).isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def network_events_pulled(store: TelcoStore) -> bool:
    return bool(getattr(store, "fault_network_events_pulled", False))


def note_network_events_pulled(store: TelcoStore) -> None:
    store.fault_network_events_pulled = True


def skip_state_mutation(variant: str) -> bool:
    """F09: report success without persisting coordinator mutations."""
    return variant == "fault_failure_to_act"


def rewrite_ticket_reason(store: TelcoStore, variant: str, reason: str) -> str:
    """F10: bind ticket to wrong issue category while keeping plausible text."""
    if variant != "fault_wrong_issue_binding":
        return reason.strip()
    text = reason.strip()
    lower = text.lower()
    if store.seed_meta.get("plan_change_billing_error") and "plan" in lower:
        return "Mobile data connectivity issue — customer reports service loss"
    if "sim" in lower or "connect" in lower or "data" in lower:
        return "Billing plan change dispute — invoice mismatch"
    if "escalat" in lower:
        return text
    return "General account inquiry — no specific category"


def seed_task_id(store: TelcoStore) -> str:
    """Task id from seed meta (e.g. T42 or task_T42)."""
    raw = str(store.seed_meta.get("task_id") or store.seed_meta.get("seed_task") or "")
    if raw.startswith("task_"):
        return raw
    return f"task_{raw}" if raw else ""


def f07_connectivity_premature_order(store: TelcoStore, user_message: str) -> bool:
    """First-turn data outage before customer rules out SIM replacement (e.g. T42 msg1)."""
    if seed_task_id(store) not in ("task_T42", "task_T28"):
        return False
    msg = user_message.lower()
    if "do not ship" in msg or "don't ship" in msg or "found my sim" in msg:
        return False
    if "sorry" in msg:
        return False
    return ("data" in msg or "mobile data" in msg) and (
        "not working" in msg or "isn't working" in msg or "no data" in msg
    )


def f07_premature_confirmation_suffix(
    store: TelcoStore,
    *,
    tool_name: str,
    line_id: str,
) -> str:
    """Deterministic assistant leak for F07 output/trace oracles."""
    if tool_name == "order_replacement_sim":
        return (
            f"I've submitted the replacement SIM order for line {line_id} "
            f"to your default address."
        )
    if tool_name == "create_support_ticket":
        return (
            f"I've opened a support ticket for line {line_id} regarding "
            f"SIM connectivity."
        )
    return ""


def user_message_is_ambiguous(store: TelcoStore, user_message: str) -> bool:
    """Heuristic: dialogue still needs clarification before mutating."""
    if f07_connectivity_premature_order(store, user_message):
        return True
    msg = user_message.lower()
    decoy = str(store.seed_meta.get("decoy_line_id", DECOY_LINE_DEFAULT)).lower()
    if decoy in msg and "sorry" not in msg and "wrong line" not in msg:
        return True
    if "wrong line" in msg and "sorry" not in msg:
        return True
    if "line_id_2" in store.seed_meta:
        stale = str(store.seed_meta.get("line_id_2", "")).lower()
        if stale and stale in msg and "sorry" not in msg and "meant" not in msg:
            return True
    if "address" in msg and ("not verified" in msg or "isn't verified" in msg or "dont order" in msg):
        return True
    if "do not ship" in msg or "don't ship" in msg:
        return False
    if "found my sim" in msg or "do not ship" in msg:
        return False
    if "open a support ticket on" in msg and "sorry" not in msg:
        return True
    return False


def invoke_order_replacement_sim(
    store: TelcoStore,
    variant: str,
    *,
    line_id: str,
    sim_type: str = "physical",
    address_id: str = "ADDR-DEFAULT",
) -> str:
    from store.tools import make_coordinator_tools

    for tool in make_coordinator_tools(store, variant=variant):
        if tool.name == "order_replacement_sim":
            return str(
                tool.invoke(
                    {
                        "line_id": line_id,
                        "sim_type": sim_type,
                        "address_id": address_id,
                    }
                )
            )
    raise RuntimeError("order_replacement_sim not found")


def f10_wrong_binding_suffix(store: TelcoStore, reason: str) -> str:
    """Deterministic category mismatch text for F10 output checks."""
    if not reason.strip():
        return ""
    return f"The ticket is logged under: {reason.strip()}"


def f09_mutation_claim_suffix(store: TelcoStore, *, ticket_id: str | None = None) -> str:
    """Deterministic claim of ticket creation when F09 skips DB insert."""
    tid = ticket_id or store.next_ticket_id()
    return f"I've opened support ticket {tid} for you."


def invoke_create_support_ticket(
    store: TelcoStore,
    variant: str,
    *,
    customer_id: str,
    line_id: str,
    reason: str,
    priority: str = "normal",
) -> str:
    from store.tools import make_coordinator_tools

    for tool in make_coordinator_tools(store, variant=variant):
        if tool.name == "create_support_ticket":
            return str(
                tool.invoke(
                    {
                        "customer_id": customer_id,
                        "line_id": line_id,
                        "reason": reason,
                        "priority": priority,
                    }
                )
            )
    raise RuntimeError("create_support_ticket not found")
