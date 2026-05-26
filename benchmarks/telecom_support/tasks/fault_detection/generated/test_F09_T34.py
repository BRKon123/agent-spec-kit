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
async def store_f09_t34():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T34")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _msg(store_f09_t34):
    meta = store_f09_t34.seed_meta
    return (
        f"I'd like to book a store appointment at store STR-001 — please run a line diagnostic "
        f"and schedule the visit in the same reply."
        f" Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )


_T34_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call("run_line_diagnostic"),
    m.tool_call("schedule_store_appointment"),
]

_T34_OUTPUT = m.contains("appointment")



@ek.fixture
async def fault_agent_f09_t34(store_f09_t34):
    yield wrap_reference_agent(store_f09_t34, variant='fault_failure_to_act')

@ek.scenario(

    agent_fixture="fault_agent_f09_t34",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F09",

        "task:T34",

        "oracle:F",

        "mutant:fault_failure_to_act",

    ),

    timeout_s=420.0,

)

async def test_f09_t34_full(s, store_f09_t34):

    (
        s.user_message(_msg(store_f09_t34))
        .assert_tool_calls(_T34_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_appointment_exists(store_f09_t34))
        .assert_output(_T34_OUTPUT)
    )





@ek.scenario(

    agent_fixture="fault_agent_f09_t34",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F09",

        "task:T34",

        "oracle:T",

        "mutant:fault_failure_to_act",

    ),

    timeout_s=420.0,

)

async def test_f09_t34_trace(s, store_f09_t34):

    (
        s.user_message(_msg(store_f09_t34))
        .assert_tool_calls(_T34_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_appointment_exists(store_f09_t34))
    )





@ek.scenario(

    agent_fixture="fault_agent_f09_t34",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F09",

        "task:T34",

        "oracle:S",

        "mutant:fault_failure_to_act",

    ),

    timeout_s=420.0,

)

async def test_f09_t34_state(s, store_f09_t34):

    (
        s.user_message(_msg(store_f09_t34))
        .assert_that(lambda: o.assert_appointment_exists(store_f09_t34))
    )





@ek.scenario(

    agent_fixture="fault_agent_f09_t34",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F09",

        "task:T34",

        "oracle:O",

        "mutant:fault_failure_to_act",

    ),

    timeout_s=420.0,

)

async def test_f09_t34_output(s, store_f09_t34):

    (
        s.user_message(_msg(store_f09_t34))
        .assert_output(_T34_OUTPUT)
    )


