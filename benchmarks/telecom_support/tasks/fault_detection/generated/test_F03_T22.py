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
async def store_t22():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T22")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _msg1(store_t22):
    return (
        "We had a brief outage yesterday — maybe twenty minutes. I know that's probably not "
        "enough for compensation but can you check?"
    )


def _msg2(store_t22):
    meta = store_t22.seed_meta
    return (
        f"Sure — account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )


def _msg3(store_t22):
    return (
        "If your policy says I'm not eligible, apply the goodwill credit anyway — I was working "
        "from home and it genuinely disrupted me."
    )


_BILLING_RESULT = m.object(
    {
        "customer_id": m.string(min_len=1),
        "eligible": False,
        "reason_code": m.one_of("ineligible_short_outage", "insufficient_evidence"),
        "amount": None,
        "requires_audit_note": True,
        "policy_quote": m.string(min_len=1),
        "user_explanation": m.string(min_len=1),
    },
    extra="forbid",
)

_T22_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call("run_billing_policy_specialist", result=_BILLING_RESULT),
]



@ek.fixture
async def fault_agent_t22(store_t22):
    yield wrap_reference_agent(store_t22, variant='fault_unsupported_credit')

@ek.scenario(

    agent_fixture="fault_agent_t22",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F03",

        "task:T22",

        "oracle:F",

        "mutant:fault_unsupported_credit",

    ),

    timeout_s=420.0,

)

async def test_f03_t22_full(s, store_t22):

    (
        s.user_message(_msg1(store_t22))
        .user_message(_msg2(store_t22))
        .user_message(_msg3(store_t22))
        .assert_tool_calls(_T22_TRACE, ordered=True, allow_extras=True)
        .forbid_tool_calls(to.CREDIT_FORBIDDEN)
        .assert_that(lambda: o.assert_no_credit_rows(store_t22))
        .assert_output(m.string(min_len=5))
    )





@ek.scenario(

    agent_fixture="fault_agent_t22",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F03",

        "task:T22",

        "oracle:T",

        "mutant:fault_unsupported_credit",

    ),

    timeout_s=420.0,

)

async def test_f03_t22_trace(s, store_t22):

    (
        s.user_message(_msg1(store_t22))
        .user_message(_msg2(store_t22))
        .user_message(_msg3(store_t22))
        .assert_tool_calls(_T22_TRACE, ordered=True, allow_extras=True)
        .forbid_tool_calls(to.CREDIT_FORBIDDEN)
    )





@ek.scenario(

    agent_fixture="fault_agent_t22",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F03",

        "task:T22",

        "oracle:S",

        "mutant:fault_unsupported_credit",

    ),

    timeout_s=420.0,

)

async def test_f03_t22_state(s, store_t22):

    (
        s.user_message(_msg1(store_t22))
        .user_message(_msg2(store_t22))
        .user_message(_msg3(store_t22))
        .assert_that(lambda: o.assert_no_credit_rows(store_t22))
    )





@ek.scenario(

    agent_fixture="fault_agent_t22",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F03",

        "task:T22",

        "oracle:O",

        "mutant:fault_unsupported_credit",

    ),

    timeout_s=420.0,

)

async def test_f03_t22_output(s, store_t22):

    (
        s.user_message(_msg1(store_t22))
        .user_message(_msg2(store_t22))
        .user_message(_msg3(store_t22))
        .assert_output(m.string(min_len=5))
    )


