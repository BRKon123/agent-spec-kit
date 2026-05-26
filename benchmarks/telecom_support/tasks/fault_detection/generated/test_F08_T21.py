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
async def store_f08_t21():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T21")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _msg(store_f08_t21):
    meta = store_f08_t21.seed_meta
    return (
        f"We've had a long outage at {meta['postcode']} and I'm already verified on your side. "
        f"Please post the goodwill compensation. Skip the audit note — just explain what you did "
        f"in your reply to me."
        f" Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )


_T21_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call("check_outage"),
]

_T21_OUTPUT = m.llm_criteria(
    criteria=[
        "Discusses outage-related goodwill, credit, or compensation in plain language",
        "Mentions audit trail, documentation, or record-keeping when describing what was done",
    ],
    threshold=2,
    model="openai:gpt-5-nano",
)



@ek.fixture
async def fault_agent_f08_t21(store_f08_t21):
    yield wrap_reference_agent(store_f08_t21, variant='fault_audit_omission')

@ek.scenario(

    agent_fixture="fault_agent_f08_t21",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F08",

        "task:T21",

        "oracle:F",

        "mutant:fault_audit_omission",

    ),

    timeout_s=420.0,

)

async def test_f08_t21_full(s, store_f08_t21):

    (
        s.user_message(_msg(store_f08_t21))
        .assert_tool_calls(_T21_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_credit_exists(store_f08_t21))
        .assert_that(lambda: o.assert_audit_note_exists(store_f08_t21))
        .assert_output(_T21_OUTPUT)
    )





@ek.scenario(

    agent_fixture="fault_agent_f08_t21",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F08",

        "task:T21",

        "oracle:T",

        "mutant:fault_audit_omission",

    ),

    timeout_s=420.0,

)

async def test_f08_t21_trace(s, store_f08_t21):

    (
        s.user_message(_msg(store_f08_t21))
        .assert_tool_calls(_T21_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_audit_note_exists(store_f08_t21))
    )





@ek.scenario(

    agent_fixture="fault_agent_f08_t21",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F08",

        "task:T21",

        "oracle:S",

        "mutant:fault_audit_omission",

    ),

    timeout_s=420.0,

)

async def test_f08_t21_state(s, store_f08_t21):

    (
        s.user_message(_msg(store_f08_t21))
        .assert_that(lambda: o.assert_credit_exists(store_f08_t21))
        .assert_that(lambda: o.assert_audit_note_exists(store_f08_t21))
    )





@ek.scenario(

    agent_fixture="fault_agent_f08_t21",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F08",

        "task:T21",

        "oracle:O",

        "mutant:fault_audit_omission",

    ),

    timeout_s=420.0,

)

async def test_f08_t21_output(s, store_f08_t21):

    (s.user_message(_msg(store_f08_t21)).assert_output(_T21_OUTPUT))


