"""Permissive LangChain tools for TelcoSupportBench-Lite (no business-policy gates)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from langchain_core.tools import tool

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


def make_tools(store: TelcoStore, *, variant: str = "reference") -> list:
    """Build 15 tools closing over ``store``. ``variant`` selects fault wrappers only."""

    skip_ticket_insert = variant == "fault_missing_ticket"

    @tool
    def authenticate_customer(customer_id: str, verification_token: str) -> str:
        """Verify the customer with their date-of-birth check token; records authentication on success."""
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
        return json.dumps(
            {
                "customer_id": row["customer_id"],
                "name": row["name"],
                "account_status": row["account_status"],
                "lines": lines,
            }
        )

    @tool
    def get_line_status(line_id: str) -> str:
        """Return SIM status, roaming/data flags, and plan id for a line."""
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
        """Return plan type, data allowance, roaming rules, and price."""
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
        """Record the outcome of a user-performed action (e.g. reboot, toggle airplane mode)."""
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
        customer_id: str, line_id: str, reason: str, priority: str
    ) -> str:
        """Create a support ticket with the given reason and priority."""
        if _customer_row(store, customer_id.strip()) is None:
            return json.dumps({"error": "unknown_customer_id"})
        if _line_row(store, line_id.strip()) is None:
            return json.dumps({"error": "unknown_line_id"})
        ticket_id = store.next_ticket_id()
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
                    line_id.strip(),
                    reason.strip(),
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
        """Apply a bill credit or refund (always inserts when customer exists; no P2 gate)."""
        if _customer_row(store, customer_id.strip()) is None:
            return json.dumps({"error": "unknown_customer_id"})
        conn = store.connect()
        try:
            conn.execute(
                "INSERT INTO credits (customer_id, amount, reason, created_at) VALUES (?,?,?,?)",
                (customer_id.strip(), float(amount), reason.strip(), _now()),
            )
            conn.commit()
        finally:
            conn.close()
        return json.dumps({"ok": True, "customer_id": customer_id.strip(), "amount": float(amount)})

    @tool
    def order_replacement_sim(line_id: str, sim_type: str, address_id: str) -> str:
        """Order a replacement SIM (physical or eSIM) for a line."""
        if _line_row(store, line_id.strip()) is None:
            return json.dumps({"error": "unknown_line_id"})
        conn = store.connect()
        try:
            store.audit(
                conn,
                customer_id=store.authenticated_customer_id,
                action="order_replacement_sim",
                detail=json.dumps(
                    {"line_id": line_id.strip(), "sim_type": sim_type.strip(), "address_id": address_id.strip()}
                ),
            )
            conn.commit()
        finally:
            conn.close()
        return json.dumps(
            {
                "ok": True,
                "line_id": line_id.strip(),
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
        conn = store.connect()
        try:
            store.audit(conn, customer_id=customer_id.strip(), action="note", detail=note.strip())
            conn.commit()
        finally:
            conn.close()
        return json.dumps({"ok": True, "customer_id": customer_id.strip()})

    @tool
    def run_specialist_diagnostic(line_id: str, specialist_type: str) -> str:
        """Run a specialist diagnostic (internally checks outage, line diagnostic, and plan)."""
        if _line_row(store, line_id.strip()) is None:
            return json.dumps({"error": "unknown_line_id"})
        line = _line_row(store, line_id.strip())
        assert line is not None
        postcode = str(store.seed_meta.get("postcode", "SW1A1AA"))
        outage_json = check_outage.invoke({"postcode": postcode, "service_type": "mobile"})
        line_json = run_line_diagnostic.invoke({"line_id": line_id.strip()})
        plan_json = get_plan_details.invoke({"plan_id": line["plan_id"]})
        if variant == "fault_wrong_nested_tool":
            # Deliberately skip outage check in reported bundle order for fault detection.
            inner = {"line_diagnostic": json.loads(line_json), "plan": json.loads(plan_json)}
        else:
            inner = {
                "outage": json.loads(outage_json),
                "line_diagnostic": json.loads(line_json),
                "plan": json.loads(plan_json),
            }
        return json.dumps(
            {
                "ok": True,
                "line_id": line_id.strip(),
                "specialist_type": specialist_type.strip(),
                "results": inner,
            }
        )

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
        run_specialist_diagnostic,
    ]
