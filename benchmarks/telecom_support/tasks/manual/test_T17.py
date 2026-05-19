"""Task T17 scenarios (explicit scripted messages and checks)."""

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
async def store_t17():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T17")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t17(store_t17):
    yield wrap_reference_agent(store_t17)


def _msg1(store_t17):
    meta = store_t17.seed_meta
    return (
        f"We had a brief outage yesterday and I want something knocked off my bill for the hassle. "
        f"Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )


def _msg2(store_t17):
    meta = store_t17.seed_meta
    return (
        f"It was only a few hours but my neighbour got credited last month — "
        f"account {meta['customer_id']}, verification token {meta['verification_token']}. "
        f"Just tell me straight whether I'm eligible or not."
    )


_T17_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call("run_billing_policy_specialist"),
]

_T17_OUTPUT = m.llm_criteria(
    criteria=[
        "Clearly states the customer is not eligible for outage compensation or a bill credit",
        "Explains why in plain language rather than only refusing",
    ],
    threshold=2,
    model="openai:gpt-5-nano",
)


@ek.scenario(
    agent_fixture="task_agent_t17",
    repeats=1,
    tags=("telecom", "task:T17", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t17_full(s, store_t17):
    (
        s.user_message(_msg1(store_t17))
        .user_message(_msg2(store_t17))
        .assert_tool_calls(_T17_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_no_credit_rows(store_t17))
        .assert_output(_T17_OUTPUT)
    )


@ek.scenario(
    agent_fixture="task_agent_t17",
    repeats=1,
    tags=("telecom", "task:T17", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t17_trace(s, store_t17):
    (
        s.user_message(_msg1(store_t17))
        .user_message(_msg2(store_t17))
        .assert_tool_calls(_T17_TRACE, ordered=True, allow_extras=True)
    )


@ek.scenario(
    agent_fixture="task_agent_t17",
    repeats=1,
    tags=("telecom", "task:T17", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t17_state(s, store_t17):
    (
        s.user_message(_msg1(store_t17))
        .user_message(_msg2(store_t17))
        .assert_that(lambda: o.assert_no_credit_rows(store_t17))
    )


@ek.scenario(
    agent_fixture="task_agent_t17",
    repeats=1,
    tags=("telecom", "task:T17", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t17_output(s, store_t17):
    (
        s.user_message(_msg1(store_t17))
        .user_message(_msg2(store_t17))
        .assert_output(_T17_OUTPUT)
    )
