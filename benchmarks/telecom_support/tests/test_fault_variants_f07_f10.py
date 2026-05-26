"""Unit tests for F07–F10 fault-variant tool and wrap behavior."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parents[1]
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

from agent_wrap import wrap_reference_agent
from store.fault_variants import (
    f07_connectivity_premature_order,
    f07_premature_confirmation_suffix,
    rewrite_ticket_reason,
    seed_task_id,
    skip_state_mutation,
    user_message_is_ambiguous,
)
from store.seeds import apply_seed
from store.store import TelcoStore
from store.tools import make_coordinator_tools


@pytest.fixture
def store_t29():
    base = Path(tempfile.mkdtemp(prefix="telco_f07_"))
    telco = TelcoStore(base / "telco.sqlite")
    apply_seed(telco, "task_T29")
    yield telco


@pytest.fixture
def store_t42():
    base = Path(tempfile.mkdtemp(prefix="telco_f07_"))
    telco = TelcoStore(base / "telco.sqlite")
    apply_seed(telco, "task_T42")
    yield telco


def test_skip_state_mutation_only_f09():
    assert skip_state_mutation("fault_failure_to_act") is True
    assert skip_state_mutation("reference") is False
    assert skip_state_mutation("fault_missing_clarification") is False


def test_rewrite_ticket_reason_f10(store_t29):
    store_t29.seed_meta["plan_change_billing_error"] = True
    out = rewrite_ticket_reason(store_t29, "fault_wrong_issue_binding", "plan change billing error")
    assert "plan" not in out.lower() or "connect" in out.lower()


def test_user_message_ambiguous_t29(store_t29):
    assert user_message_is_ambiguous(store_t29, "replacement SIM for LINE-WRONG please")
    assert not user_message_is_ambiguous(
        store_t29,
        "Sorry wrong line — use LINE-0002 instead",
    )


def test_f07_connectivity_premature_t42(store_t42):
    assert seed_task_id(store_t42) == "task_T42"
    msg = "My mobile data is not working at all. Account CUST-042."
    assert f07_connectivity_premature_order(store_t42, msg)
    assert user_message_is_ambiguous(store_t42, msg)


def test_f07_confirmation_suffix():
    store = TelcoStore(Path(tempfile.mkdtemp()) / "x.sqlite")
    text = f07_premature_confirmation_suffix(
        store, tool_name="order_replacement_sim", line_id="LINE-WRONG"
    )
    assert "LINE-WRONG" in text
    assert "submitted" in text.lower()


def test_audit_omission_no_note_row(store_t29):
    store_t29.authenticated_customer_id = str(store_t29.seed_meta["customer_id"])
    tools = {t.name: t for t in make_coordinator_tools(store_t29, variant="fault_audit_omission")}
    tools["add_audit_note"].invoke({"customer_id": store_t29.authenticated_customer_id, "note": "test"})
    conn = store_t29.connect()
    try:
        cur = conn.execute("SELECT COUNT(*) FROM audit_log WHERE action = 'note'")
        assert cur.fetchone()[0] == 0
    finally:
        conn.close()


def test_failure_to_act_skips_ticket_insert(store_t29):
    store_t29.authenticated_customer_id = str(store_t29.seed_meta["customer_id"])
    cid = store_t29.authenticated_customer_id
    lid = str(store_t29.seed_meta["line_id"])
    tools = {t.name: t for t in make_coordinator_tools(store_t29, variant="fault_failure_to_act")}
    raw = tools["create_support_ticket"].invoke(
        {"customer_id": cid, "line_id": lid, "reason": "test", "priority": "normal"}
    )
    assert json.loads(raw)["ok"] is True
    conn = store_t29.connect()
    try:
        cur = conn.execute("SELECT COUNT(*) FROM tickets")
        assert cur.fetchone()[0] == 0
    finally:
        conn.close()


def test_reference_variant_unaffected(store_t29):
    agent = wrap_reference_agent(store_t29, variant="reference")
    assert agent._variant == "reference"
