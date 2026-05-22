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
async def store_t38():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T38")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)

def _msg(store_t38):
    meta = store_t38.seed_meta
    return (
        f"My connection keeps lagging on and off — can you run thorough network diagnostics "
        f"and make sure your systems are actually responding?"
        f" Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )


_T38_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call("run_network_diagnostics_specialist"),
    m.tool_call("heartbeat_ping"),
]

_T38_OUTPUT = m.string(min_len=5)



@ek.fixture
async def fault_agent_t38(store_t38):
    yield wrap_reference_agent(store_t38, variant='fault_wrong_nested_tool')

@ek.scenario(

    agent_fixture="fault_agent_t38",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F05",

        "task:T38",

        "oracle:F",

        "mutant:fault_wrong_nested_tool",

    ),

    timeout_s=420.0,

)

async def test_f05_t38_full(s, store_t38):

    (
        s.user_message(_msg(store_t38))
        .assert_tool_calls(_T38_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_no_mutations(store_t38))
        .assert_output(_T38_OUTPUT)
    )





@ek.scenario(

    agent_fixture="fault_agent_t38",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F05",

        "task:T38",

        "oracle:T",

        "mutant:fault_wrong_nested_tool",

    ),

    timeout_s=420.0,

)

async def test_f05_t38_trace(s, store_t38):

    (
        s.user_message(_msg(store_t38))
        .assert_tool_calls(_T38_TRACE, ordered=True, allow_extras=True)
    )





@ek.scenario(

    agent_fixture="fault_agent_t38",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F05",

        "task:T38",

        "oracle:S",

        "mutant:fault_wrong_nested_tool",

    ),

    timeout_s=420.0,

)

async def test_f05_t38_state(s, store_t38):

    (
        s.user_message(_msg(store_t38))
        .assert_that(lambda: o.assert_no_mutations(store_t38))
    )





@ek.scenario(

    agent_fixture="fault_agent_t38",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F05",

        "task:T38",

        "oracle:O",

        "mutant:fault_wrong_nested_tool",

    ),

    timeout_s=420.0,

)

async def test_f05_t38_output(s, store_t38):

    (
        s.user_message(_msg(store_t38))
        .assert_output(_T38_OUTPUT)
    )


