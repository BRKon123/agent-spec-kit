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
async def store_t23():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T23")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _msg(store_t23):
    meta = store_t23.seed_meta
    return (
        f"I think I was charged twice for the same roaming add-on. Can you check whether I'm owed "
        f"a refund and tell me how much — but don't actually post anything to my bill yet?"
        f" Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )


_T23_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call(
        "run_billing_policy_specialist",
        result=m.object({"eligible": True, "amount": m.number(min=0.01)}, extra="forbid"),
    ),
]

_T23_OUTPUT = m.llm_criteria(
    criteria=[
        "States whether the customer is eligible for a credit or refund (eligible or not eligible)",
        "Mentions a specific dollar or currency amount for the refund or credit",
    ],
    threshold=2,
    model="openai:gpt-5-nano",
)



@ek.fixture
async def fault_agent_t23(store_t23):
    yield wrap_reference_agent(store_t23, variant='fault_structured_output')

@ek.scenario(

    agent_fixture="fault_agent_t23",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F06",

        "task:T23",

        "oracle:F",

        "mutant:fault_structured_output",

    ),

    timeout_s=420.0,

)

async def test_f06_t23_full(s, store_t23):

    (
        s.user_message(_msg(store_t23))
        .assert_tool_calls(_T23_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_no_credit_rows(store_t23))
        .assert_output(_T23_OUTPUT)
    )





@ek.scenario(

    agent_fixture="fault_agent_t23",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F06",

        "task:T23",

        "oracle:T",

        "mutant:fault_structured_output",

    ),

    timeout_s=420.0,

)

async def test_f06_t23_trace(s, store_t23):

    (s.user_message(_msg(store_t23)).assert_tool_calls(_T23_TRACE, ordered=True, allow_extras=True))





@ek.scenario(

    agent_fixture="fault_agent_t23",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F06",

        "task:T23",

        "oracle:S",

        "mutant:fault_structured_output",

    ),

    timeout_s=420.0,

)

async def test_f06_t23_state(s, store_t23):

    (s.user_message(_msg(store_t23)).assert_that(lambda: o.assert_no_credit_rows(store_t23)))





@ek.scenario(

    agent_fixture="fault_agent_t23",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F06",

        "task:T23",

        "oracle:O",

        "mutant:fault_structured_output",

    ),

    timeout_s=420.0,

)

async def test_f06_t23_output(s, store_t23):

    (s.user_message(_msg(store_t23)).assert_output(_T23_OUTPUT))


