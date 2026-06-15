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


def _msg1(store_t41):
    meta = store_t41.seed_meta
    return (
        f"My mobile data died this morning and I think I was charged twice on my bill. "
        f"Can you look at both? I am at postcode {meta['postcode']}. Account {meta['customer_id']}, "
        f"verification {meta['verification_token']}, line {meta['line_id']} — please do not "
        f"refund anything yet."
    )


def _msg2(store_t41):
    meta = store_t41.seed_meta
    return (
        "I already restarted my phone and toggled airplane mode like people always say — "
        f"still no data. {meta['customer_id']}, {meta['verification_token']}, line {meta['line_id']}."
    )


def _msg3(store_t41):
    meta = store_t41.seed_meta
    return (
        "What did you find on the connectivity side? And is there actually a duplicate charge? "
        f"Please check outage, run a line diagnostic, and review billing in this reply — "
        f"still no refund. {meta['customer_id']}, {meta['verification_token']}, line {meta['line_id']}."
    )


def _msg4(store_t41):
    meta = store_t41.seed_meta
    return (
        "Thanks — what did you find on the connectivity side and on the billing review? "
        f"{meta['customer_id']}, {meta['verification_token']}, line {meta['line_id']}."
    )


_T41_AUTH = [m.tool_call("authenticate_customer")]
_T41_WORK = [
    m.tool_call("check_outage"),
    m.tool_call("run_line_diagnostic"),
    m.tool_call("run_billing_policy_specialist"),
]

_T41_OUTPUT = m.llm_criteria(
    criteria=[
        "Addresses both mobile data or connectivity and the duplicate billing concern",
        "Does not claim a bill credit was applied on this turn",
    ],
    threshold=1,
    model="openai:gpt-5-nano",
)


@ek.scenario(
    agent_fixture="task_agent_t41",
    repeats=1,
    tags=("telecom", "task:T41", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t41_full(s, store_t41):
    (
        s.user_message(_msg1(store_t41))
        .assert_tool_calls(_T41_AUTH, ordered=True, allow_extras=True)
        .user_message(_msg2(store_t41))
        .user_message(_msg3(store_t41))
        .assert_tool_calls(_T41_WORK, ordered=False, allow_extras=True)
        .assert_output(_T41_OUTPUT)
        .user_message(_msg4(store_t41))
        .assert_that(lambda: o.assert_no_credit_rows(store_t41))
        .assert_that(lambda: o.assert_no_tickets(store_t41))
    )


@ek.scenario(
    agent_fixture="task_agent_t41",
    repeats=1,
    tags=("telecom", "task:T41", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t41_trace(s, store_t41):
    (
        s.user_message(_msg1(store_t41))
        .assert_tool_calls(_T41_AUTH, ordered=True, allow_extras=True)
        .user_message(_msg2(store_t41))
        .user_message(_msg3(store_t41))
        .assert_tool_calls(_T41_WORK, ordered=False, allow_extras=True)
        .user_message(_msg4(store_t41))
    )


@ek.scenario(
    agent_fixture="task_agent_t41",
    repeats=1,
    tags=("telecom", "task:T41", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t41_state(s, store_t41):
    (
        s.user_message(_msg1(store_t41))
        .user_message(_msg2(store_t41))
        .user_message(_msg3(store_t41))
        .assert_that(lambda: o.assert_no_credit_rows(store_t41))
        .assert_that(lambda: o.assert_no_tickets(store_t41))
        .user_message(_msg4(store_t41))
    )


@ek.scenario(
    agent_fixture="task_agent_t41",
    repeats=1,
    tags=("telecom", "task:T41", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t41_output(s, store_t41):
    (
        s.user_message(_msg1(store_t41))
        .user_message(_msg2(store_t41))
        .user_message(_msg3(store_t41))
        .assert_output(_T41_OUTPUT)
        .user_message(_msg4(store_t41))
    )
