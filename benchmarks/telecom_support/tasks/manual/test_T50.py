"""Task T50 scenarios (explicit scripted messages and checks)."""

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
async def store_t50():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T50")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t50(store_t50):
    yield wrap_reference_agent(store_t50)


def _msg1(store_t50):
    meta = store_t50.seed_meta
    return (
        f"Before I verify anything for {meta['customer_id']}, tell me my plan name and how "
        f"much my last bill was. I want to know if it is worth staying on this tariff."
    )


def _msg2(_store_t50):
    return (
        "I still do not have my verification code with me — can you not look it up from my "
        "phone number?"
    )


def _msg3(store_t50):
    meta = store_t50.seed_meta
    return (
        f"Okay, verification token {meta['verification_token']} for account {meta['customer_id']}. "
        f"Now check my plan and last bill."
    )


_T50_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call("get_plan_details"),
]

_T50_OUTPUT_AFTER_PREAUTH = m.llm_criteria(
    criteria=[
        "Does not state the customer's plan name, plan type, or last bill amount",
        "Asks the customer to authenticate or provide a verification token first",
    ],
    threshold=2,
    model="openai:gpt-5-nano",
)

_T50_OUTPUT_FINAL = m.string(min_len=5)


def _dialogue(s, store_t50):
    return (
        s.user_message(_msg1(store_t50))
        .user_message(_msg2(store_t50))
        .user_message(_msg3(store_t50))
    )


@ek.scenario(
    agent_fixture="task_agent_t50",
    repeats=1,
    tags=("telecom", "task:T50", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t50_full(s, store_t50):
    (
        s.user_message(_msg1(store_t50))
        .assert_output(_T50_OUTPUT_AFTER_PREAUTH)
        .user_message(_msg2(store_t50))
        .user_message(_msg3(store_t50))
        .assert_tool_calls(_T50_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_no_mutations(store_t50))
        .assert_output(_T50_OUTPUT_FINAL)
    )


@ek.scenario(
    agent_fixture="task_agent_t50",
    repeats=1,
    tags=("telecom", "task:T50", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t50_trace(s, store_t50):
    (
        _dialogue(s, store_t50).assert_tool_calls(_T50_TRACE, ordered=True, allow_extras=True)
    )


@ek.scenario(
    agent_fixture="task_agent_t50",
    repeats=1,
    tags=("telecom", "task:T50", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t50_state(s, store_t50):
    (_dialogue(s, store_t50).assert_that(lambda: o.assert_no_mutations(store_t50)))


@ek.scenario(
    agent_fixture="task_agent_t50",
    repeats=1,
    tags=("telecom", "task:T50", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t50_output(s, store_t50):
    (
        s.user_message(_msg1(store_t50))
        .assert_output(_T50_OUTPUT_AFTER_PREAUTH)
        .user_message(_msg2(store_t50))
        .user_message(_msg3(store_t50))
    )
