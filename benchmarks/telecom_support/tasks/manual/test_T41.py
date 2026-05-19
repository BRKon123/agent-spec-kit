"""Task T41 scenarios (explicit scripted messages and checks)."""

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
async def store_t41():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T41")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t41(store_t41):
    yield wrap_reference_agent(store_t41)


def _msg1(_store_t41):
    return (
        "Hi — my mobile data has been dead since this morning and I also spotted what looks "
        "like the same plan charge twice on my last bill. Can you look at both?"
    )


def _msg2(_store_t41):
    return (
        "Please fix the data side first. I still want the billing checked, but do not put any "
        "credit or refund on my account in this chat."
    )


def _msg3(store_t41):
    meta = store_t41.seed_meta
    return (
        f"I already restarted the phone and toggled aeroplane mode — still no data. "
        f"Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}, postcode {meta.get('postcode', 'E1 6AN')}. Please check "
        f"outages, run diagnostics on the line, and "
        f"have billing review the duplicate charge in this reply. Do not apply any bill credit "
        f"and do not open a support ticket — investigation only."
    )


def _msg4(_store_t41):
    return "What did you find on the duplicate charge?"


_T41_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call("check_outage"),
    m.tool_call("run_line_diagnostic"),
    m.tool_call("run_billing_policy_specialist"),
]

_T41_OUTPUT = m.llm_criteria(
    criteria=[
        "Mentions mobile data or connectivity and something about the bill or duplicate charge",
        "Does not claim a bill credit was applied",
    ],
    threshold=1,
    model="openai:gpt-5-nano",
)


def _dialogue(s, store_t41):
    return (
        s.user_message(_msg1(store_t41))
        .user_message(_msg2(store_t41))
        .user_message(_msg3(store_t41))
    )


@ek.scenario(
    agent_fixture="task_agent_t41",
    repeats=1,
    tags=("telecom", "task:T41", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t41_full(s, store_t41):
    (
        _dialogue(s, store_t41)
        .assert_tool_calls(_T41_TRACE, ordered=False, allow_extras=True)
        .assert_that(lambda: o.assert_no_credit_rows(store_t41))
        .assert_that(lambda: o.assert_no_tickets(store_t41))
        .user_message(_msg4(store_t41))
        .assert_output(_T41_OUTPUT)
    )


@ek.scenario(
    agent_fixture="task_agent_t41",
    repeats=1,
    tags=("telecom", "task:T41", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t41_trace(s, store_t41):
    (_dialogue(s, store_t41).assert_tool_calls(_T41_TRACE, ordered=False, allow_extras=True))


@ek.scenario(
    agent_fixture="task_agent_t41",
    repeats=1,
    tags=("telecom", "task:T41", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t41_state(s, store_t41):
    (
        _dialogue(s, store_t41)
        .assert_that(lambda: o.assert_no_credit_rows(store_t41))
        .assert_that(lambda: o.assert_no_tickets(store_t41))
    )


@ek.scenario(
    agent_fixture="task_agent_t41",
    repeats=1,
    tags=("telecom", "task:T41", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t41_output(s, store_t41):
    (
        _dialogue(s, store_t41)
        .user_message(_msg4(store_t41))
        .assert_output(_T41_OUTPUT)
    )
