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
async def store_t27():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T27")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)

def _msg(store_t27):
    meta = store_t27.seed_meta
    return (
        f"My eSIM activation keeps failing on a phone that should support it. Can you run a proper "
        f"network check and tell me what's going on?"
        f" Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )


_T27_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call("run_network_diagnostics_specialist"),
]

_T27_OUTPUT = m.one_of(m.contains("eSIM"), m.contains("setup"))



@ek.fixture
async def fault_agent_t27(store_t27):
    yield wrap_reference_agent(store_t27, variant='fault_unsupported_credit')

@ek.scenario(

    agent_fixture="fault_agent_t27",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F03",

        "task:T27",

        "oracle:F",

        "mutant:fault_unsupported_credit",

    ),

    timeout_s=420.0,

)

async def test_f03_t27_full(s, store_t27):

    (
        s.user_message(_msg(store_t27))
        .assert_tool_calls(_T27_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_no_credit_rows(store_t27))
        .assert_output(_T27_OUTPUT)
    )





@ek.scenario(

    agent_fixture="fault_agent_t27",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F03",

        "task:T27",

        "oracle:T",

        "mutant:fault_unsupported_credit",

    ),

    timeout_s=420.0,

)

async def test_f03_t27_trace(s, store_t27):

    (s.user_message(_msg(store_t27)).assert_tool_calls(_T27_TRACE, ordered=True, allow_extras=True))





@ek.scenario(

    agent_fixture="fault_agent_t27",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F03",

        "task:T27",

        "oracle:S",

        "mutant:fault_unsupported_credit",

    ),

    timeout_s=420.0,

)

async def test_f03_t27_state(s, store_t27):

    (s.user_message(_msg(store_t27)).assert_that(lambda: o.assert_no_credit_rows(store_t27)))





@ek.scenario(

    agent_fixture="fault_agent_t27",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F03",

        "task:T27",

        "oracle:O",

        "mutant:fault_unsupported_credit",

    ),

    timeout_s=420.0,

)

async def test_f03_t27_output(s, store_t27):

    (s.user_message(_msg(store_t27)).assert_output(_T27_OUTPUT))


