"""Generated fault-detection scenarios — do not edit by hand.

Regenerate: uv run python benchmarks/telecom_support/scripts/bootstrap_fault_detection.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import agent_spec_kit as ek
import agent_spec_kit.match as m
from tasks.specs import oracles as o
from tasks.specs import trace_oracles as to
from agent_wrap import wrap_reference_agent



import shutil
import tempfile

from store.seeds import apply_seed
from store.store import TelcoStore

@ek.fixture
async def store_t43():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T43")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _msg1(store_t43):
    return "My SIM will not connect — it is the family line, I think the number ends in 4421?"


def _msg2(store_t43):
    return "Sorry, wrong line — I meant our other phone, the one ending 7788."


def _msg3(store_t43):
    meta = store_t43.seed_meta
    return (
        f"Yes please use {meta['line_id']} for anything you do. "
        f"Account {meta['customer_id']}, verification {meta['verification_token']}."
    )



@ek.fixture
async def fault_agent_t43(store_t43):
    yield wrap_reference_agent(store_t43, variant='fault_stale_belief')

@ek.scenario(

    agent_fixture="fault_agent_t43",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F02",

        "task:T43",

        "oracle:F",

        "mutant:fault_stale_belief",

    ),

    timeout_s=420.0,

)

async def test_f02_t43_full(s, store_t43):

    (
        s.user_message(_msg1(store_t43))
        .user_message(_msg2(store_t43))
        .user_message(_msg3(store_t43))
        .assert_that(lambda: o.assert_no_ticket_on_line(store_t43, "LINE-WRONG"))
        .assert_output(m.string(min_len=5))
    )





@ek.scenario(

    agent_fixture="fault_agent_t43",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F02",

        "task:T43",

        "oracle:T",

        "mutant:fault_stale_belief",

    ),

    timeout_s=420.0,

)

async def test_f02_t43_trace(s, store_t43):

    (
        s.user_message(_msg1(store_t43))
        .user_message(_msg2(store_t43))
        .user_message(_msg3(store_t43))
        .assert_tool_calls([m.tool_call("authenticate_customer")], ordered=True, allow_extras=True)
    )





@ek.scenario(

    agent_fixture="fault_agent_t43",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F02",

        "task:T43",

        "oracle:S",

        "mutant:fault_stale_belief",

    ),

    timeout_s=420.0,

)

async def test_f02_t43_state(s, store_t43):

    (
        s.user_message(_msg1(store_t43))
        .user_message(_msg2(store_t43))
        .user_message(_msg3(store_t43))
        .assert_that(lambda: o.assert_no_ticket_on_line(store_t43, "LINE-WRONG"))
    )





@ek.scenario(

    agent_fixture="fault_agent_t43",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F02",

        "task:T43",

        "oracle:O",

        "mutant:fault_stale_belief",

    ),

    timeout_s=420.0,

)

async def test_f02_t43_output(s, store_t43):

    (
        s.user_message(_msg1(store_t43))
        .user_message(_msg2(store_t43))
        .user_message(_msg3(store_t43))
        .assert_output(m.string(min_len=5))
    )


