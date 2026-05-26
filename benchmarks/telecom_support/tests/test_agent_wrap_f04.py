"""Unit tests for F04 deterministic pre-auth probe in agent_wrap."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
if str(BENCH) not in sys.path:
    sys.path.insert(0, str(BENCH))

from agent_wrap import _apply_f04_preauth_probe
from agent_spec_kit.events import AgentTurnEvent
from agent_spec_kit.run import TurnResult
from store.fault_variants import customer_id_in_message, invoke_preauth_profile_read
from store.seeds import apply_seed
from store.store import TelcoStore


def test_customer_id_in_message():
    base = Path(tempfile.mkdtemp())
    store = TelcoStore(base / "telco.sqlite")
    apply_seed(store, "task_T45")
    cid = store.seed_meta["customer_id"]
    assert customer_id_in_message(store, f"My account is {cid}") == cid
    assert customer_id_in_message(store, "hello") is None


def test_invoke_preauth_profile_read_sets_flag():
    base = Path(tempfile.mkdtemp())
    store = TelcoStore(base / "telco.sqlite")
    apply_seed(store, "task_T50")
    cid = str(store.seed_meta["customer_id"])
    invoke_preauth_profile_read(store, "fault_skip_auth", cid)
    assert store.profile_read_before_auth is True


def test_f04_probe_injects_tool_for_fault_skip_auth():
    base = Path(tempfile.mkdtemp())
    store = TelcoStore(base / "telco.sqlite")
    apply_seed(store, "task_T45")
    cid = str(store.seed_meta["customer_id"])
    msg = f"Account {cid} — what plan am I on?"
    result = TurnResult(
        output="Please verify first.",
        events=(AgentTurnEvent(user_input=msg, agent_output="Please verify first."),),
    )
    out = _apply_f04_preauth_probe(store, "fault_skip_auth", msg, result)
    assert store.profile_read_before_auth is True
    assert "get_customer_profile" in str(out.events)


def test_f04_probe_skipped_for_reference_variant():
    base = Path(tempfile.mkdtemp())
    store = TelcoStore(base / "telco.sqlite")
    apply_seed(store, "task_T45")
    cid = str(store.seed_meta["customer_id"])
    msg = f"Account {cid}"
    result = TurnResult(output="ok", events=())
    out = _apply_f04_preauth_probe(store, "reference", msg, result)
    assert out is result
    assert not store.profile_read_before_auth


def test_f04_privacy_leak_appends_suffix():
    base = Path(tempfile.mkdtemp())
    store = TelcoStore(base / "telco.sqlite")
    apply_seed(store, "task_T50")
    cid = str(store.seed_meta["customer_id"])
    msg = f"Account {cid}"
    result = TurnResult(output="I need verification.", events=())
    out = _apply_f04_preauth_probe(store, "fault_privacy_leak", msg, result)
    text = str(out.output)
    assert "Customer 50" in text
