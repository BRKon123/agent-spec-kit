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
async def store_f08_t26():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T26")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _msg(store_f08_t26):
    meta = store_f08_t26.seed_meta
    return (
        f"I lost my physical SIM card — can you send a replacement to my usual home address for "
        f"line {meta['line_id']}?"
        f" Account {meta['customer_id']}, verification token {meta['verification_token']}."
    )


_T26_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call(
        "order_replacement_sim",
        args=m.object({"sim_type": m.one_of("physical")}, extra="ignore"),
    ),
]

_T26_OUTPUT = m.one_of(m.contains("replacement"), m.contains("SIM"))



@ek.fixture
async def fault_agent_f08_t26(store_f08_t26):
    yield wrap_reference_agent(store_f08_t26, variant='fault_audit_omission')

@ek.scenario(

    agent_fixture="fault_agent_f08_t26",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F08",

        "task:T26",

        "oracle:F",

        "mutant:fault_audit_omission",

    ),

    timeout_s=420.0,

)

async def test_f08_t26_full(s, store_f08_t26):

    (
        s.user_message(_msg(store_f08_t26))
        .assert_tool_calls(_T26_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_sim_order_exists(store_f08_t26))
        .assert_that(lambda: o.assert_audit_note_exists(store_f08_t26))
        .assert_output(_T26_OUTPUT)
    )





@ek.scenario(

    agent_fixture="fault_agent_f08_t26",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F08",

        "task:T26",

        "oracle:T",

        "mutant:fault_audit_omission",

    ),

    timeout_s=420.0,

)

async def test_f08_t26_trace(s, store_f08_t26):

    (
        s.user_message(_msg(store_f08_t26))
        .assert_tool_calls(_T26_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_audit_note_exists(store_f08_t26))
    )





@ek.scenario(

    agent_fixture="fault_agent_f08_t26",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F08",

        "task:T26",

        "oracle:S",

        "mutant:fault_audit_omission",

    ),

    timeout_s=420.0,

)

async def test_f08_t26_state(s, store_f08_t26):

    (
        s.user_message(_msg(store_f08_t26))
        .assert_that(lambda: o.assert_sim_order_exists(store_f08_t26))
        .assert_that(lambda: o.assert_audit_note_exists(store_f08_t26))
    )





@ek.scenario(

    agent_fixture="fault_agent_f08_t26",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F08",

        "task:T26",

        "oracle:O",

        "mutant:fault_audit_omission",

    ),

    timeout_s=420.0,

)

async def test_f08_t26_output(s, store_f08_t26):

    (s.user_message(_msg(store_f08_t26)).assert_output(_T26_OUTPUT))


