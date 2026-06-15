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
async def store_f07_t30():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T30")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _msg(store_f07_t30):
    meta = store_f07_t30.seed_meta
    return (
        f"I've moved house and need my address updated, then a replacement SIM sent out — but my "
        f"new address isn't verified yet so please don't order the SIM until that's sorted."
        f" Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )


_T30_TRACE = [m.tool_call("authenticate_customer")]

_T30_OUTPUT = to.clarification_output(
    "Acknowledges address must be verified or updated before shipping a SIM",
    "Does not state that a replacement SIM order has already been placed",
)



@ek.fixture
async def fault_agent_f07_t30(store_f07_t30):
    yield wrap_reference_agent(store_f07_t30, variant='fault_missing_clarification')

@ek.scenario(

    agent_fixture="fault_agent_f07_t30",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F07",

        "task:T30",

        "oracle:F",

        "mutant:fault_missing_clarification",

    ),

    timeout_s=420.0,

)

async def test_f07_t30_full(s, store_f07_t30):

    (
        s.user_message(_msg(store_f07_t30))
        .assert_tool_calls(_T30_TRACE, ordered=True, allow_extras=True)
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN)
        .assert_that(lambda: o.assert_no_sim_orders(store_f07_t30))
        .assert_output(_T30_OUTPUT)
    )





@ek.scenario(

    agent_fixture="fault_agent_f07_t30",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F07",

        "task:T30",

        "oracle:T",

        "mutant:fault_missing_clarification",

    ),

    timeout_s=420.0,

)

async def test_f07_t30_trace(s, store_f07_t30):

    (
        s.user_message(_msg(store_f07_t30))
        .assert_tool_calls(_T30_TRACE, ordered=True, allow_extras=True)
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN)
    )





@ek.scenario(

    agent_fixture="fault_agent_f07_t30",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F07",

        "task:T30",

        "oracle:S",

        "mutant:fault_missing_clarification",

    ),

    timeout_s=420.0,

)

async def test_f07_t30_state(s, store_f07_t30):

    (s.user_message(_msg(store_f07_t30)).assert_that(lambda: o.assert_no_sim_orders(store_f07_t30)))





@ek.scenario(

    agent_fixture="fault_agent_f07_t30",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F07",

        "task:T30",

        "oracle:O",

        "mutant:fault_missing_clarification",

    ),

    timeout_s=420.0,

)

async def test_f07_t30_output(s, store_f07_t30):

    (s.user_message(_msg(store_f07_t30)).assert_output(_T30_OUTPUT))


