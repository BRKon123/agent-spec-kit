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
async def store_f09_t35():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T35")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _msg(store_f09_t35):
    meta = store_f09_t35.seed_meta
    return (
        f"I already have open ticket TCK-EXIST-01 for this — please escalate that one, "
        f"don't open a duplicate."
        f" Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )


_T35_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call("escalate_ticket"),
]

_T35_OUTPUT = m.one_of(m.contains("escalat"), m.contains("policy"))



@ek.fixture
async def fault_agent_f09_t35(store_f09_t35):
    yield wrap_reference_agent(store_f09_t35, variant='fault_failure_to_act')

@ek.scenario(

    agent_fixture="fault_agent_f09_t35",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F09",

        "task:T35",

        "oracle:F",

        "mutant:fault_failure_to_act",

    ),

    timeout_s=420.0,

)

async def test_f09_t35_full(s, store_f09_t35):

    (
        s.user_message(_msg(store_f09_t35))
        .assert_tool_calls(_T35_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_ticket_count(store_f09_t35, 1))
        .assert_output(_T35_OUTPUT)
    )





@ek.scenario(

    agent_fixture="fault_agent_f09_t35",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F09",

        "task:T35",

        "oracle:T",

        "mutant:fault_failure_to_act",

    ),

    timeout_s=420.0,

)

async def test_f09_t35_trace(s, store_f09_t35):

    (
        s.user_message(_msg(store_f09_t35))
        .assert_tool_calls(_T35_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_ticket_count(store_f09_t35, 1))
    )





@ek.scenario(

    agent_fixture="fault_agent_f09_t35",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F09",

        "task:T35",

        "oracle:S",

        "mutant:fault_failure_to_act",

    ),

    timeout_s=420.0,

)

async def test_f09_t35_state(s, store_f09_t35):

    (
        s.user_message(_msg(store_f09_t35))
        .assert_that(lambda: o.assert_ticket_count(store_f09_t35, 1))
    )





@ek.scenario(

    agent_fixture="fault_agent_f09_t35",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F09",

        "task:T35",

        "oracle:O",

        "mutant:fault_failure_to_act",

    ),

    timeout_s=420.0,

)

async def test_f09_t35_output(s, store_f09_t35):

    (
        s.user_message(_msg(store_f09_t35))
        .assert_output(_T35_OUTPUT)
    )


