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

from agent_wrap import wrap_reference_agent




import shutil
import tempfile

from store.seeds import apply_seed
from store.store import TelcoStore

@ek.fixture
async def store_t05():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T05")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)

def _msg(store_t05):
    meta = store_t05.seed_meta
    return (
        f"My line {meta['line_id']} keeps lagging with latency spikes — can you check if it's "
        f"the network side? "
        f"Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )


_T05_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call("run_network_diagnostics_specialist"),
]

_T05_OUTPUT = m.one_of(
    m.contains("latency"),
    m.contains("spike"),
    m.contains("congestion"),
    m.contains("diagnostic"),
    m.contains("network"),
)



@ek.fixture
async def fault_agent_t05(store_t05):
    yield wrap_reference_agent(store_t05, variant='fault_wrong_nested_tool')

@ek.scenario(

    agent_fixture="fault_agent_t05",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F05",

        "task:T05",

        "oracle:F",

        "mutant:fault_wrong_nested_tool",

    ),

    timeout_s=420.0,

)

async def test_f05_t05_full(s, store_t05):

    (
        s.user_message(_msg(store_t05))
        .assert_tool_calls(_T05_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_no_credit_rows(store_t05))
        .assert_output(_T05_OUTPUT)
    )





@ek.scenario(

    agent_fixture="fault_agent_t05",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F05",

        "task:T05",

        "oracle:T",

        "mutant:fault_wrong_nested_tool",

    ),

    timeout_s=420.0,

)

async def test_f05_t05_trace(s, store_t05):

    (s.user_message(_msg(store_t05)).assert_tool_calls(_T05_TRACE, ordered=True, allow_extras=True))





@ek.scenario(

    agent_fixture="fault_agent_t05",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F05",

        "task:T05",

        "oracle:S",

        "mutant:fault_wrong_nested_tool",

    ),

    timeout_s=420.0,

)

async def test_f05_t05_state(s, store_t05):

    (s.user_message(_msg(store_t05)).assert_that(lambda: o.assert_no_credit_rows(store_t05)))





@ek.scenario(

    agent_fixture="fault_agent_t05",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F05",

        "task:T05",

        "oracle:O",

        "mutant:fault_wrong_nested_tool",

    ),

    timeout_s=420.0,

)

async def test_f05_t05_output(s, store_t05):

    (s.user_message(_msg(store_t05)).assert_output(_T05_OUTPUT))


