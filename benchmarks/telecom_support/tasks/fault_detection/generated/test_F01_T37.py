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
async def store_t37():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T37")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)

def _msg1(store_t37):
    meta = store_t37.seed_meta
    return (
        f"My line diagnostic failed earlier — can you walk me through a device restart?"
        f" Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )

def _msg2(store_t37):
    meta = store_t37.seed_meta
    return (
        f"Done — I restarted the phone on line {meta['line_id']}. "
        f"Please carry on and open a support ticket with whatever the diagnostic showed."
    )


_T37_TRACE = [
    m.tool_call("record_user_action"),
    m.tool_call("run_line_diagnostic"),
    m.tool_call("create_support_ticket"),
]

_T37_OUTPUT = m.contains("ticket")



@ek.fixture
async def fault_agent_t37(store_t37):
    yield wrap_reference_agent(store_t37, variant='fault_premature_escalate')

@ek.scenario(

    agent_fixture="fault_agent_t37",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F01",

        "task:T37",

        "oracle:F",

        "mutant:fault_premature_escalate",

    ),

    timeout_s=420.0,

)

async def test_f01_t37_full(s, store_t37):

    (
        s.user_message(_msg1(store_t37))
        .user_message(_msg2(store_t37))
        .assert_tool_calls(_T37_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_ticket_exists(store_t37))
        .assert_output(_T37_OUTPUT)
    )





@ek.scenario(

    agent_fixture="fault_agent_t37",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F01",

        "task:T37",

        "oracle:T",

        "mutant:fault_premature_escalate",

    ),

    timeout_s=420.0,

)

async def test_f01_t37_trace(s, store_t37):

    (
        s.user_message(_msg1(store_t37))
        .user_message(_msg2(store_t37))
        .assert_tool_calls(_T37_TRACE, ordered=True, allow_extras=True)
    )





@ek.scenario(

    agent_fixture="fault_agent_t37",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F01",

        "task:T37",

        "oracle:S",

        "mutant:fault_premature_escalate",

    ),

    timeout_s=420.0,

)

async def test_f01_t37_state(s, store_t37):

    (
        s.user_message(_msg1(store_t37))
        .user_message(_msg2(store_t37))
        .assert_that(lambda: o.assert_ticket_exists(store_t37))
    )





@ek.scenario(

    agent_fixture="fault_agent_t37",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F01",

        "task:T37",

        "oracle:O",

        "mutant:fault_premature_escalate",

    ),

    timeout_s=420.0,

)

async def test_f01_t37_output(s, store_t37):

    (
        s.user_message(_msg1(store_t37))
        .user_message(_msg2(store_t37))
        .assert_output(_T37_OUTPUT)
    )


