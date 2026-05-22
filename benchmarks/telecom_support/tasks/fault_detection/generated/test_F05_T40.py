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
async def store_t40():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T40")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)

def _msg(store_t40):
    meta = store_t40.seed_meta
    return (
        f"My signal keeps dropping out — please pull recent network events for my line "
        f"before you score how unusual the signal looks."
        f" Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )


_T40_SPECIALIST = m.tool_call(
    "run_network_diagnostics_specialist",
    children=[
        m.tool_call("pull_network_events"),
        m.tool_call("score_signal_anomaly"),
    ],
)

_T40_TRACE = [
    m.tool_call("authenticate_customer"),
    _T40_SPECIALIST,
]

_T40_OUTPUT = m.llm_criteria(
    criteria=[
        "Acknowledges intermittent signal drops or connectivity issues",
        "References network diagnostics or investigation (not a definite root cause unless evidence supports it)",
    ],
    threshold=2,
    model="openai:gpt-5-nano",
)



@ek.fixture
async def fault_agent_t40(store_t40):
    yield wrap_reference_agent(store_t40, variant='fault_wrong_nested_tool')

@ek.scenario(

    agent_fixture="fault_agent_t40",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F05",

        "task:T40",

        "oracle:F",

        "mutant:fault_wrong_nested_tool",

    ),

    timeout_s=420.0,

)

async def test_f05_t40_full(s, store_t40):

    (
        s.user_message(_msg(store_t40))
        .assert_tool_calls(_T40_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_no_mutations(store_t40))
        .assert_output(_T40_OUTPUT)
    )





@ek.scenario(

    agent_fixture="fault_agent_t40",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F05",

        "task:T40",

        "oracle:T",

        "mutant:fault_wrong_nested_tool",

    ),

    timeout_s=420.0,

)

async def test_f05_t40_trace(s, store_t40):

    (
        s.user_message(_msg(store_t40))
        .assert_tool_calls(_T40_TRACE, ordered=True, allow_extras=True)
    )





@ek.scenario(

    agent_fixture="fault_agent_t40",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F05",

        "task:T40",

        "oracle:S",

        "mutant:fault_wrong_nested_tool",

    ),

    timeout_s=420.0,

)

async def test_f05_t40_state(s, store_t40):

    (
        s.user_message(_msg(store_t40))
        .assert_that(lambda: o.assert_no_mutations(store_t40))
    )





@ek.scenario(

    agent_fixture="fault_agent_t40",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F05",

        "task:T40",

        "oracle:O",

        "mutant:fault_wrong_nested_tool",

    ),

    timeout_s=420.0,

)

async def test_f05_t40_output(s, store_t40):

    (
        s.user_message(_msg(store_t40))
        .assert_output(_T40_OUTPUT)
    )


