"""Permissive LangChain tools for TelcoSupportBench (no business-policy gates)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Literal

from langchain_core.tools import BaseTool, tool

from store.fault_variants import (
    enrich_profile_payload,
    mark_preauth_sensitive_read,
    note_line_mention,
    note_network_events_pulled,
    network_events_pulled,
    resolve_mutation_line,
    rewrite_ticket_reason,
    skip_state_mutation,
)
from store.store import TelcoStore


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _customer_row(store: TelcoStore, customer_id: str) -> dict[str, Any] | None:
    conn = store.connect()
    try:
        cur = conn.execute("SELECT * FROM customers WHERE customer_id = ?", (customer_id,))
        return store.row_to_dict(cur.fetchone())
    finally:
        conn.close()


def _line_row(store: TelcoStore, line_id: str) -> dict[str, Any] | None:
    conn = store.connect()
    try:
        cur = conn.execute("SELECT * FROM lines WHERE line_id = ?", (line_id,))
        return store.row_to_dict(cur.fetchone())
    finally:
        conn.close()


def make_coordinator_tools(store: TelcoStore, *, variant: str = "reference") -> list[BaseTool]:
    """Root coordinator tools (15) plus heartbeat_ping; specialist delegates added in agents/reference.py."""

    skip_ticket_insert = variant in ("fault_missing_ticket", "fault_failure_to_act")
    skip_mutation_insert = skip_state_mutation(variant)

    @tool
    def authenticate_customer(customer_id: str, verification_token: str) -> str:
        """Verify the customer with their date-of-birth check token; records authentication on success.

        Call at most once per conversation. If the customer repeats credentials on a later turn,
        the session is already authenticated — proceed with other tools instead of calling again.
        """
        row = _customer_row(store, customer_id.strip())
        if row is None:
            return json.dumps({"ok": False, "error": "unknown_customer_id"})
        if row["dob_check_token"] != verification_token.strip():
            return json.dumps({"ok": False, "error": "invalid_verification_token"})
        store.authenticated_customer_id = customer_id.strip()
        conn = store.connect()
        try:
            store.audit(
                conn,
                customer_id=customer_id.strip(),
                action="authenticate",
                detail="customer authenticated",
            )
            conn.commit()
        finally:
            conn.close()
        return json.dumps({"ok": True, "customer_id": customer_id.strip()})

    @tool
    def get_customer_profile(customer_id: str) -> str:
        """Return customer name, account status, and linked line ids (no auth gate)."""
        mark_preauth_sensitive_read(store, variant)
        row = _customer_row(store, customer_id.strip())
        if row is None:
            return json.dumps({"error": "unknown_customer_id"})
        conn = store.connect()
        try:
            cur = conn.execute(
                "SELECT line_id, phone_number, plan_id, sim_status FROM lines WHERE customer_id = ?",
                (customer_id.strip(),),
            )
            lines = [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()
        payload = enrich_profile_payload(
            store,
            variant,
            {
                "customer_id": row["customer_id"],
                "name": row["name"],
                "account_status": row["account_status"],
                "lines": lines,
            },
            customer_row=row,
        )
        return json.dumps(payload)

    @tool
    def get_line_status(line_id: str) -> str:
        """Return SIM status, roaming/data flags, and plan id for a line.

        When the user asks to check both plan and line (especially roaming abroad),
        call this tool first, then get_plan_details for the returned plan_id.
        """
        mark_preauth_sensitive_read(store, variant)
        row = _line_row(store, line_id.strip())
        if row is None:
            return json.dumps({"error": "unknown_line_id"})
        return json.dumps(
            {
                "line_id": row["line_id"],
                "customer_id": row["customer_id"],
                "phone_number": row["phone_number"],
                "plan_id": row["plan_id"],
                "sim_status": row["sim_status"],
                "roaming_enabled": bool(row["roaming_enabled"]),
                "data_enabled": bool(row["data_enabled"]),
            }
        )

    @tool
    def get_plan_details(plan_id: str) -> str:
        """Return plan type, data allowance, roaming rules, and price.

        Call after get_line_status when both plan limits and line flags are needed.
        """
        mark_preauth_sensitive_read(store, variant)
        conn = store.connect()
        try:
            cur = conn.execute("SELECT * FROM plans WHERE plan_id = ?", (plan_id.strip(),))
            row = store.row_to_dict(cur.fetchone())
        finally:
            conn.close()
        if row is None:
            return json.dumps({"error": "unknown_plan_id"})
        return json.dumps(
            {
                "plan_id": row["plan_id"],
                "plan_type": row["plan_type"],
                "data_allowance_mb": row["data_allowance_mb"],
                "roaming_rules": json.loads(row["roaming_rules_json"]),
                "price": row["price"],
            }
        )

    @tool
    def check_outage(postcode: str, service_type: str) -> str:
        """List known network outages for a postcode and service type."""
        conn = store.connect()
        try:
            cur = conn.execute(
                "SELECT id, postcode, service_type, status, started_at, affected_services_json "
                "FROM network_outages WHERE postcode = ? AND service_type = ?",
                (postcode.strip().upper(), service_type.strip().lower()),
            )
            rows = [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()
        return json.dumps({"postcode": postcode.strip().upper(), "service_type": service_type, "outages": rows})

    @tool
    def run_line_diagnostic(line_id: str) -> str:
        """Run line/network diagnostic and store results."""
        effective = resolve_mutation_line(store, variant, line_id)
        row = _line_row(store, effective)
        if row is None:
            return json.dumps({"error": "unknown_line_id"})
        result = {
            "line_id": effective,
            "sim_status": row["sim_status"],
            "data_enabled": bool(row["data_enabled"]),
            "roaming_enabled": bool(row["roaming_enabled"]),
            "signal": "weak" if not row["data_enabled"] else "ok",
        }
        conn = store.connect()
        try:
            conn.execute(
                "INSERT INTO diagnostics (line_id, kind, result_json, created_at) VALUES (?,?,?,?)",
                (effective, "line", json.dumps(result), _now()),
            )
            conn.commit()
        finally:
            conn.close()
        return json.dumps({"ok": True, "diagnostic": result})

    @tool
    def send_troubleshooting_step(line_id: str, step: str) -> str:
        """Record that the agent instructed the user to perform a troubleshooting step."""
        if _line_row(store, line_id.strip()) is None:
            return json.dumps({"error": "unknown_line_id"})
        conn = store.connect()
        try:
            conn.execute(
                "INSERT INTO usage_events (line_id, event_type, detail, occurred_at) VALUES (?,?,?,?)",
                (line_id.strip(), "troubleshoot_step", step.strip(), _now()),
            )
            conn.commit()
        finally:
            conn.close()
        return json.dumps({"ok": True, "line_id": line_id.strip(), "step": step.strip()})

    @tool
    def record_user_action(line_id: str, action: str, result: str) -> str:
        """Record the outcome of a user-performed action (e.g. reboot, toggle airplane mode).

        When the user confirms they restarted the phone or completed a troubleshooting step,
        call this before create_support_ticket in the same agent turn.
        """
        line = _line_row(store, line_id.strip())
        if line is None:
            return json.dumps({"error": "unknown_line_id"})
        conn = store.connect()
        try:
            conn.execute(
                "INSERT INTO usage_events (line_id, event_type, detail, occurred_at) VALUES (?,?,?,?)",
                (line_id.strip(), f"user_action:{action.strip()}", result.strip(), _now()),
            )
            if action.strip() in ("toggle_airplane_mode", "disable_airplane_mode", "restart_phone"):
                cur = conn.execute(
                    "SELECT settings_json FROM devices WHERE line_id = ? LIMIT 1",
                    (line_id.strip(),),
                )
                dev = cur.fetchone()
                if dev is not None:
                    settings = store.parse_settings(dev["settings_json"])
                    if action.strip() == "toggle_airplane_mode":
                        settings["airplane_mode"] = not settings.get("airplane_mode", False)
                    elif action.strip() == "disable_airplane_mode":
                        settings["airplane_mode"] = False
                    elif action.strip() == "restart_phone":
                        settings["restarted"] = True
                    conn.execute(
                        "UPDATE devices SET settings_json = ? WHERE line_id = ?",
                        (store.dump_settings(settings), line_id.strip()),
                    )
            conn.commit()
        finally:
            conn.close()
        return json.dumps({"ok": True, "line_id": line_id.strip(), "action": action.strip(), "result": result})

    @tool
    def create_support_ticket(
        customer_id: str,
        line_id: str,
        reason: str,
        priority: str = "normal",
    ) -> str:
        """Create a support ticket with the given reason and priority.

        Pass priority as its own argument ("normal" or "high") — do not embed it in reason.

        After the user confirms a restart or troubleshooting step, call record_user_action
        first, then this tool in the same turn. Use a reason that mentions diagnostic findings.
        """
        if _customer_row(store, customer_id.strip()) is None:
            return json.dumps({"error": "unknown_customer_id"})
        effective_line = resolve_mutation_line(store, variant, line_id)
        if variant == "fault_stale_belief":
            note_line_mention(store, line_id)
        if _line_row(store, effective_line) is None:
            return json.dumps({"error": "unknown_line_id"})
        ticket_id = store.next_ticket_id()
        effective_reason = rewrite_ticket_reason(store, variant, reason)
        if skip_ticket_insert:
            return json.dumps({"ok": True, "ticket_id": ticket_id, "status": "open"})
        conn = store.connect()
        try:
            conn.execute(
                "INSERT INTO tickets (ticket_id, customer_id, line_id, reason, priority, status, created_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (
                    ticket_id,
                    customer_id.strip(),
                    effective_line,
                    effective_reason,
                    priority.strip(),
                    "open",
                    _now(),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return json.dumps({"ok": True, "ticket_id": ticket_id, "status": "open"})

    @tool
    def escalate_ticket(ticket_id: str, escalation_reason: str) -> str:
        """Escalate an existing ticket with a reason."""
        conn = store.connect()
        try:
            cur = conn.execute("SELECT ticket_id FROM tickets WHERE ticket_id = ?", (ticket_id.strip(),))
            if cur.fetchone() is None:
                return json.dumps({"error": "unknown_ticket_id"})
            if skip_mutation_insert:
                return json.dumps({"ok": True, "ticket_id": ticket_id.strip(), "status": "escalated"})
            conn.execute(
                "UPDATE tickets SET status = ?, reason = reason || ' | ESCALATION: ' || ? WHERE ticket_id = ?",
                ("escalated", escalation_reason.strip(), ticket_id.strip()),
            )
            conn.commit()
        finally:
            conn.close()
        return json.dumps({"ok": True, "ticket_id": ticket_id.strip(), "status": "escalated"})

    @tool
    def apply_bill_credit(customer_id: str, amount: float, reason: str) -> str:
        """Apply a bill credit or refund to the account.

        Use only after run_billing_policy_specialist returns eligible=True and the user has not
        asked for assessment-only or said not to post credit yet. Do not use for short-outage
        ineligible cases or when the user instructs a wrong customer_id for the specialist.
        """
        if _customer_row(store, customer_id.strip()) is None:
            return json.dumps({"error": "unknown_customer_id"})
        credit_amount = float(amount) if amount else 25.0
        if variant == "fault_unsupported_credit" and credit_amount <= 0:
            credit_amount = 25.0
        if skip_mutation_insert:
            return json.dumps({"ok": True, "customer_id": customer_id.strip(), "amount": credit_amount})
        conn = store.connect()
        try:
            conn.execute(
                "INSERT INTO credits (customer_id, amount, reason, created_at) VALUES (?,?,?,?)",
                (customer_id.strip(), credit_amount, reason.strip(), _now()),
            )
            conn.commit()
        finally:
            conn.close()
        return json.dumps({"ok": True, "customer_id": customer_id.strip(), "amount": credit_amount})

    @tool
    def order_replacement_sim(line_id: str, sim_type: str, address_id: str) -> str:
        """Order a replacement SIM (physical or eSIM) for a line."""
        effective = resolve_mutation_line(store, variant, line_id)
        if variant == "fault_stale_belief":
            note_line_mention(store, line_id)
        if _line_row(store, effective) is None:
            return json.dumps({"error": "unknown_line_id"})
        order_id = store.next_sim_order_id()
        if skip_mutation_insert:
            return json.dumps(
                {
                    "ok": True,
                    "order_id": order_id,
                    "line_id": effective,
                    "sim_type": sim_type.strip(),
                    "address_id": address_id.strip(),
                }
            )
        conn = store.connect()
        try:
            conn.execute(
                "INSERT INTO sim_orders (order_id, line_id, sim_type, address_id, status, created_at) "
                "VALUES (?,?,?,?,?,?)",
                (
                    order_id,
                    effective,
                    sim_type.strip(),
                    address_id.strip(),
                    "ordered",
                    _now(),
                ),
            )
            store.audit(
                conn,
                customer_id=store.authenticated_customer_id,
                action="order_replacement_sim",
                detail=json.dumps(
                    {
                        "order_id": order_id,
                        "line_id": effective,
                        "sim_type": sim_type.strip(),
                        "address_id": address_id.strip(),
                    }
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return json.dumps(
            {
                "ok": True,
                "order_id": order_id,
                "line_id": effective,
                "sim_type": sim_type.strip(),
                "address_id": address_id.strip(),
            }
        )

    @tool
    def schedule_store_appointment(customer_id: str, store_id: str, reason: str) -> str:
        """Schedule an in-store appointment."""
        if _customer_row(store, customer_id.strip()) is None:
            return json.dumps({"error": "unknown_customer_id"})
        conn = store.connect()
        try:
            conn.execute(
                "INSERT INTO appointments (customer_id, store_id, reason, scheduled_at) VALUES (?,?,?,?)",
                (customer_id.strip(), store_id.strip(), reason.strip(), _now()),
            )
            conn.commit()
            cur = conn.execute("SELECT last_insert_rowid()")
            appt_id = int(cur.fetchone()[0])
        finally:
            conn.close()
        return json.dumps({"ok": True, "appointment_id": appt_id, "store_id": store_id.strip()})

    @tool
    def add_audit_note(customer_id: str, note: str) -> str:
        """Append an audit note for a customer."""
        if variant == "fault_audit_omission":
            return json.dumps({"ok": True, "customer_id": customer_id.strip()})
        conn = store.connect()
        try:
            store.audit(conn, customer_id=customer_id.strip(), action="note", detail=note.strip())
            conn.commit()
        finally:
            conn.close()
        return json.dumps({"ok": True, "customer_id": customer_id.strip()})

    @tool
    def heartbeat_ping() -> str:
        """Health check sidecar; call alongside get_line_status when the user asks for a quick line check."""
        return json.dumps({"status": "ok", "heartbeat": "ping"})

    return [
        authenticate_customer,
        get_customer_profile,
        get_line_status,
        get_plan_details,
        check_outage,
        run_line_diagnostic,
        send_troubleshooting_step,
        record_user_action,
        create_support_ticket,
        escalate_ticket,
        apply_bill_credit,
        order_replacement_sim,
        schedule_store_appointment,
        add_audit_note,
        heartbeat_ping,
    ]


def make_network_specialist_tools(store: TelcoStore, *, variant: str = "reference") -> list[BaseTool]:
    """Nested tools for NetworkDiagnosticsSpecialist subgraph."""

    validate_anomaly_args = variant != "fault_wrong_nested_tool"

    @tool
    def pull_network_events(line_id: str, window_minutes: int) -> str:
        """Pull recent network events for a line within a time window."""
        if _line_row(store, line_id.strip()) is None:
            return json.dumps({"error": "unknown_line_id"})
        note_network_events_pulled(store)
        conn = store.connect()
        try:
            cur = conn.execute(
                "SELECT event_type, detail, occurred_at FROM network_events WHERE line_id = ? "
                "ORDER BY occurred_at DESC LIMIT 50",
                (line_id.strip(),),
            )
            events = [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()
        return json.dumps(
            {
                "line_id": line_id.strip(),
                "window_minutes": window_minutes,
                "events": events,
                "count": len(events),
            }
        )

    @tool
    def check_outage(postcode: str, service_type: str) -> str:
        """List known network outages for a postcode and service type."""
        conn = store.connect()
        try:
            cur = conn.execute(
                "SELECT id, postcode, service_type, status, started_at, affected_services_json "
                "FROM network_outages WHERE postcode = ? AND service_type = ?",
                (postcode.strip().upper(), service_type.strip().lower()),
            )
            rows = [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()
        return json.dumps({"postcode": postcode.strip().upper(), "service_type": service_type, "outages": rows})

    @tool
    def run_line_diagnostic(line_id: str) -> str:
        """Run line/network diagnostic and store results."""
        row = _line_row(store, line_id.strip())
        if row is None:
            return json.dumps({"error": "unknown_line_id"})
        result = {
            "line_id": line_id.strip(),
            "sim_status": row["sim_status"],
            "data_enabled": bool(row["data_enabled"]),
            "roaming_enabled": bool(row["roaming_enabled"]),
            "signal": "weak" if not row["data_enabled"] else "ok",
        }
        conn = store.connect()
        try:
            conn.execute(
                "INSERT INTO diagnostics (line_id, kind, result_json, created_at) VALUES (?,?,?,?)",
                (line_id.strip(), "line", json.dumps(result), _now()),
            )
            conn.commit()
        finally:
            conn.close()
        return json.dumps({"ok": True, "diagnostic": result})

    @tool
    def score_signal_anomaly(
        source: Literal["events", "synthetic"],
        anomaly_score: float,
        window_minutes: int | None = None,
        override_reason: str | None = None,
    ) -> str:
        """Score signal anomaly from events or synthetic source."""
        if validate_anomaly_args:
            if source == "events" and window_minutes is None:
                raise ValueError("window_minutes required when source is events")
            if source == "events" and override_reason:
                raise ValueError("override_reason forbidden when source is events")
        return json.dumps(
            {
                "anomaly_score": anomaly_score,
                "risk_band": "elevated" if anomaly_score >= 0.5 else "low",
                "source": source,
                "window_minutes": window_minutes,
                "nested_order_fault": variant == "fault_wrong_nested_tool",
            }
        )

    @tool
    def classify_fault_domain(line_id: str) -> str:
        """Classify likely fault domain from line state and seed context."""
        row = _line_row(store, line_id.strip())
        if row is None:
            return json.dumps({"error": "unknown_line_id"})
        domain = str(store.seed_meta.get("fault_domain", "unknown"))
        if domain == "unknown":
            if not row["data_enabled"]:
                domain = "device"
            elif not row["roaming_enabled"] and store.seed_meta.get("roaming_issue"):
                domain = "roaming"
            elif store.seed_meta.get("network_outage_active"):
                domain = "network"
        return json.dumps({"line_id": line_id.strip(), "fault_domain": domain})

    return [
        pull_network_events,
        check_outage,
        run_line_diagnostic,
        score_signal_anomaly,
        classify_fault_domain,
    ]


def make_billing_specialist_tools(store: TelcoStore, *, variant: str = "reference") -> list[BaseTool]:
    """Nested tools for BillingPolicySpecialist subgraph."""

    del variant  # reserved for billing fault variants

    @tool
    def pull_billing_events(customer_id: str, window_days: int) -> str:
        """Pull recent billing events for a customer."""
        if _customer_row(store, customer_id.strip()) is None:
            return json.dumps({"error": "unknown_customer_id"})
        conn = store.connect()
        try:
            cur = conn.execute(
                "SELECT event_type, amount, detail, occurred_at FROM billing_events "
                "WHERE customer_id = ? ORDER BY occurred_at DESC LIMIT 50",
                (customer_id.strip(),),
            )
            events = [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()
        return json.dumps(
            {
                "customer_id": customer_id.strip(),
                "window_days": window_days,
                "events": events,
                "count": len(events),
            }
        )

    @tool
    def classify_credit_eligibility(customer_id: str) -> str:
        """Classify whether the customer is eligible for a credit under policy."""
        if _customer_row(store, customer_id.strip()) is None:
            return json.dumps({"error": "unknown_customer_id"})
        meta = store.seed_meta
        if meta.get("duplicate_charge"):
            code = "duplicate_charge"
            eligible = True
        elif meta.get("credit_eligible"):
            code = "verified_long_outage"
            eligible = True
        elif meta.get("plan_change_billing_error"):
            code = "plan_change_error"
            eligible = False
        elif meta.get("short_outage"):
            code = "ineligible_short_outage"
            eligible = False
        else:
            code = "insufficient_evidence"
            eligible = False
        return json.dumps(
            {
                "customer_id": customer_id.strip(),
                "eligible": eligible,
                "reason_code": code,
            }
        )

    @tool
    def calculate_credit_amount(customer_id: str, reason_code: str) -> str:
        """Calculate credit amount when eligible."""
        amount = float(store.seed_meta.get("credit_amount", 0.0))
        return json.dumps(
            {
                "customer_id": customer_id.strip(),
                "reason_code": reason_code.strip(),
                "amount": amount,
            }
        )

    return [pull_billing_events, classify_credit_eligibility, calculate_credit_amount]


def make_tools(store: TelcoStore, *, variant: str = "reference") -> list[BaseTool]:
    """Backward-compatible alias: coordinator tools only."""
    return make_coordinator_tools(store, variant=variant)
