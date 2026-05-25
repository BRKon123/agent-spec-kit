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
async def store_t46():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T46")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _msg1(store_t46):
    return "Please open a support ticket on LINE-WRONG — my work phone keeps dropping calls."


def _msg2(store_t46):
    return "Sorry, that is my old line — I meant my current work phone instead."


def _msg3(store_t46):
    meta = store_t46.seed_meta
    return (
        f"Yes use {meta['line_id']}. Account {meta['customer_id']}, verification "
        f"{meta['verification_token']} — go ahead with the ticket on that line."
    )



@ek.fixture
async def fault_agent_t46(store_t46):
    yield wrap_reference_agent(store_t46, variant='fault_stale_belief')

@ek.scenario(

    agent_fixture="fault_agent_t46",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F02",

        "task:T46",

        "oracle:F",

        "mutant:fault_stale_belief",

    ),

    timeout_s=420.0,

)

async def test_f02_t46_full(s, store_t46):

    meta = store_t46.seed_meta
    (
        s.user_message(_msg1(store_t46))
        .user_message(_msg2(store_t46))
        .user_message(_msg3(store_t46))
        .assert_tool_calls(
            [
                m.tool_call("authenticate_customer"),
                to.ticket_on_line(meta["line_id"]),
            ],
            ordered=True,
            allow_extras=True,
        )
        .assert_that(lambda: o.assert_no_ticket_on_line(store_t46, "LINE-WRONG"))
        .assert_that(lambda: o.assert_ticket_for_line(store_t46, meta["line_id"]))
    )





@ek.scenario(

    agent_fixture="fault_agent_t46",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F02",

        "task:T46",

        "oracle:T",

        "mutant:fault_stale_belief",

    ),

    timeout_s=420.0,

)

async def test_f02_t46_trace(s, store_t46):

    meta = store_t46.seed_meta
    (
        s.user_message(_msg1(store_t46))
        .user_message(_msg2(store_t46))
        .user_message(_msg3(store_t46))
        .assert_tool_calls(
            [
                m.tool_call("authenticate_customer"),
                to.ticket_on_line(meta["line_id"]),
            ],
            ordered=True,
            allow_extras=True,
        )
    )





@ek.scenario(

    agent_fixture="fault_agent_t46",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F02",

        "task:T46",

        "oracle:S",

        "mutant:fault_stale_belief",

    ),

    timeout_s=420.0,

)

async def test_f02_t46_state(s, store_t46):

    meta = store_t46.seed_meta
    (
        s.user_message(_msg1(store_t46))
        .user_message(_msg2(store_t46))
        .user_message(_msg3(store_t46))
        .assert_that(lambda: o.assert_ticket_for_line(store_t46, meta["line_id"]))
    )





@ek.scenario(

    agent_fixture="fault_agent_t46",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F02",

        "task:T46",

        "oracle:O",

        "mutant:fault_stale_belief",

    ),

    timeout_s=420.0,

)

async def test_f02_t46_output(s, store_t46):

    (
        s.user_message(_msg1(store_t46))
        .user_message(_msg2(store_t46))
        .user_message(_msg3(store_t46))
        .assert_output(m.string(min_len=5))
    )


