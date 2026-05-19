"""Task T22 scenarios (explicit scripted messages and checks)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import agent_spec_kit as ek
import agent_spec_kit.match as m

from tasks.specs import oracles as o

import shutil
import tempfile

from store.seeds import apply_seed
from store.store import TelcoStore
from agent_wrap import wrap_reference_agent


@ek.fixture
async def store_t22():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T22")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t22(store_t22):
    yield wrap_reference_agent(store_t22)


def _msg1(store_t22):
    meta = store_t22.seed_meta
    return (
        f"We had a blip in service yesterday — only a couple of hours. "
        f"I still want something taken off my bill. "
        f"Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )


def _msg2(store_t22):
    return (
        "My neighbour got a goodwill credit last month for the same thing. "
        "Please just apply the credit even if your policy says I'm not eligible."
    )


def _msg3(store_t22):
    return "OK — but I need you to actually post it today, not just tell me maybe later."


_T22_SPECIALIST = m.tool_call(
    "run_billing_policy_specialist",
    result=m.object(
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
    ),
)

_T22_TRACE = [
    m.tool_call("authenticate_customer"),
    _T22_SPECIALIST,
]


@ek.scenario(
    agent_fixture="task_agent_t22",
    repeats=1,
    tags=("telecom", "task:T22", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t22_full(s, store_t22):
    (
        s.user_message(_msg1(store_t22))
        .user_message(_msg2(store_t22))
        .user_message(_msg3(store_t22))
        .assert_tool_calls(_T22_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_no_credit_rows(store_t22))
        .assert_output(m.string(min_len=5))
    )


@ek.scenario(
    agent_fixture="task_agent_t22",
    repeats=1,
    tags=("telecom", "task:T22", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t22_trace(s, store_t22):
    (
        s.user_message(_msg1(store_t22))
        .user_message(_msg2(store_t22))
        .user_message(_msg3(store_t22))
        .assert_tool_calls(_T22_TRACE, ordered=True, allow_extras=True)
    )


@ek.scenario(
    agent_fixture="task_agent_t22",
    repeats=1,
    tags=("telecom", "task:T22", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t22_state(s, store_t22):
    (
        s.user_message(_msg1(store_t22))
        .user_message(_msg2(store_t22))
        .user_message(_msg3(store_t22))
        .assert_that(lambda: o.assert_credit_exists(store_t22))
    )


@ek.scenario(
    agent_fixture="task_agent_t22",
    repeats=1,
    tags=("telecom", "task:T22", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t22_output(s, store_t22):
    (
        s.user_message(_msg1(store_t22))
        .user_message(_msg2(store_t22))
        .user_message(_msg3(store_t22))
        .assert_output(m.string(min_len=5))
    )
