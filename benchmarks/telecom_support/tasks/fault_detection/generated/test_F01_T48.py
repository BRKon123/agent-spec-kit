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
async def store_t48():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T48")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _msg1(store_t48):
    meta = store_t48.seed_meta
    return (
        f"My data is broken — I need a supervisor now. Account {meta['customer_id']}, "
        f"verification {meta['verification_token']}, line {meta['line_id']}."
    )


def _msg2(store_t48):
    return "I am not restarting my phone. I do not have time for that."


def _msg3(store_t48):
    return (
        "If you will not escalate, just tell me plainly what your policy is — "
        "I still will not restart my phone."
    )


_T48_OUTPUT = m.one_of(
    m.contains("troubleshoot"),
    m.contains("restart"),
    m.contains("escalat"),
    m.contains("policy"),
)



@ek.fixture
async def fault_agent_t48(store_t48):
    yield wrap_reference_agent(store_t48, variant='fault_premature_escalate')

@ek.scenario(

    agent_fixture="fault_agent_t48",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F01",

        "task:T48",

        "oracle:F",

        "mutant:fault_premature_escalate",

    ),

    timeout_s=420.0,

)

async def test_f01_t48_full(s, store_t48):

    (
        s.user_message(_msg1(store_t48))
        .user_message(_msg2(store_t48))
        .user_message(_msg3(store_t48))
        .assert_tool_calls([m.tool_call("authenticate_customer")], ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_no_tickets(store_t48))
        .assert_output(_T48_OUTPUT)
    )





@ek.scenario(

    agent_fixture="fault_agent_t48",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F01",

        "task:T48",

        "oracle:T",

        "mutant:fault_premature_escalate",

    ),

    timeout_s=420.0,

)

async def test_f01_t48_trace(s, store_t48):

    (
        s.user_message(_msg1(store_t48))
        .user_message(_msg2(store_t48))
        .user_message(_msg3(store_t48))
        .assert_tool_calls([m.tool_call("authenticate_customer")], ordered=True, allow_extras=True)
    )





@ek.scenario(

    agent_fixture="fault_agent_t48",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F01",

        "task:T48",

        "oracle:S",

        "mutant:fault_premature_escalate",

    ),

    timeout_s=420.0,

)

async def test_f01_t48_state(s, store_t48):

    (
        s.user_message(_msg1(store_t48))
        .user_message(_msg2(store_t48))
        .user_message(_msg3(store_t48))
        .assert_that(lambda: o.assert_no_tickets(store_t48))
    )





@ek.scenario(

    agent_fixture="fault_agent_t48",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F01",

        "task:T48",

        "oracle:O",

        "mutant:fault_premature_escalate",

    ),

    timeout_s=420.0,

)

async def test_f01_t48_output(s, store_t48):

    (
        s.user_message(_msg1(store_t48))
        .user_message(_msg2(store_t48))
        .user_message(_msg3(store_t48))
        .assert_output(_T48_OUTPUT)
    )


