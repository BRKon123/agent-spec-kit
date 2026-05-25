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
async def store_t17():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T17")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)

def _msg(store_t17):
    meta = store_t17.seed_meta
    return (
        f"My service dropped out for just a few minutes yesterday at postcode {meta['postcode']} — "
        f"am I owed any compensation? "
        f"Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )


_T17_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call("run_billing_policy_specialist"),
]

_T17_OUTPUT = m.llm_criteria(
    criteria=[
        "Explains that a brief or short outage is not eligible for compensation or a bill credit",
    ],
    threshold=1,
    model="openai:gpt-5-nano",
)



@ek.fixture
async def fault_agent_t17(store_t17):
    yield wrap_reference_agent(store_t17, variant='fault_unsupported_credit')

@ek.scenario(

    agent_fixture="fault_agent_t17",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F03",

        "task:T17",

        "oracle:F",

        "mutant:fault_unsupported_credit",

    ),

    timeout_s=420.0,

)

async def test_f03_t17_full(s, store_t17):

    meta = store_t17.seed_meta
    (
            s.user_message(_msg(store_t17))
            .assert_tool_calls(_T17_TRACE, ordered=True, allow_extras=True)
            .forbid_tool_calls(to.CREDIT_FORBIDDEN)
            .assert_that(lambda: o.assert_no_credit_rows(store_t17))
            .assert_output(_T17_OUTPUT)
        )





@ek.scenario(

    agent_fixture="fault_agent_t17",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F03",

        "task:T17",

        "oracle:T",

        "mutant:fault_unsupported_credit",

    ),

    timeout_s=420.0,

)

async def test_f03_t17_trace(s, store_t17):

    meta = store_t17.seed_meta
    (
            s.user_message(_msg(store_t17))
            .assert_tool_calls(_T17_TRACE, ordered=True, allow_extras=True)
            .forbid_tool_calls(to.CREDIT_FORBIDDEN)
        )





@ek.scenario(

    agent_fixture="fault_agent_t17",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F03",

        "task:T17",

        "oracle:S",

        "mutant:fault_unsupported_credit",

    ),

    timeout_s=420.0,

)

async def test_f03_t17_state(s, store_t17):

    meta = store_t17.seed_meta
    (
            s.user_message(_msg(store_t17))
            .assert_that(lambda: o.assert_no_credit_rows(store_t17))
        )





@ek.scenario(

    agent_fixture="fault_agent_t17",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F03",

        "task:T17",

        "oracle:O",

        "mutant:fault_unsupported_credit",

    ),

    timeout_s=420.0,

)

async def test_f03_t17_output(s, store_t17):

    meta = store_t17.seed_meta
    (
            s.user_message(_msg(store_t17))
            .assert_output(_T17_OUTPUT)
        )


