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
