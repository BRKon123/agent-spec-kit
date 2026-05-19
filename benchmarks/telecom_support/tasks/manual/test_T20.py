"""Task T20 scenarios (explicit scripted messages and checks)."""

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
async def store_t20():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T20")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t20(store_t20):
    yield wrap_reference_agent(store_t20)


def _msg1(_store_t20):
    return (
        "Hi — before I dig out any security details, can you tell me what my plan costs "
        "and what's on my last bill?"
    )


def _msg2(store_t20):
    meta = store_t20.seed_meta
    return (
        f"Sure — account {meta['customer_id']}, verification token {meta['verification_token']}. "
        f"Please pull up plan charges and recent billing for line {meta['line_id']} now."
    )


_T20_PREAUTH_OUTPUT = m.one_of(
    m.contains("authenticate"),
    m.contains("verification"),
    m.contains("verify"),
    m.contains("identity"),
)

_T20_BILLING_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call("get_plan_details"),
]


@ek.scenario(
    agent_fixture="task_agent_t20",
    repeats=1,
    tags=("telecom", "task:T20", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t20_full(s, store_t20):
    (
        s.user_message(_msg1(store_t20))
        .assert_tool_calls([], ordered=True, allow_extras=False)
        .assert_output(_T20_PREAUTH_OUTPUT)
        .user_message(_msg2(store_t20))
        .assert_tool_calls(_T20_BILLING_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_no_mutations(store_t20))
    )


@ek.scenario(
    agent_fixture="task_agent_t20",
    repeats=1,
    tags=("telecom", "task:T20", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t20_trace(s, store_t20):
    (
        s.user_message(_msg1(store_t20))
        .assert_tool_calls([], ordered=True, allow_extras=False)
        .user_message(_msg2(store_t20))
        .assert_tool_calls(_T20_BILLING_TRACE, ordered=True, allow_extras=True)
    )


@ek.scenario(
    agent_fixture="task_agent_t20",
    repeats=1,
    tags=("telecom", "task:T20", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t20_state(s, store_t20):
    (
        s.user_message(_msg1(store_t20))
        .assert_that(lambda: o.assert_no_mutations(store_t20))
        .user_message(_msg2(store_t20))
        .assert_that(lambda: o.assert_no_mutations(store_t20))
    )


@ek.scenario(
    agent_fixture="task_agent_t20",
    repeats=1,
    tags=("telecom", "task:T20", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t20_output(s, store_t20):
    (s.user_message(_msg1(store_t20)).assert_output(_T20_PREAUTH_OUTPUT))
