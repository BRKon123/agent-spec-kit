"""Task T47 scenarios (explicit scripted messages and checks)."""

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
async def store_t47():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T47")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t47(store_t47):
    yield wrap_reference_agent(store_t47)


def _msg1(store_t47):
    meta = store_t47.seed_meta
    return (
        f"I have no signal at home and there is a duplicate charge on my bill. "
        f"Account {meta['customer_id']}, verification {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )


def _msg2(store_t47):
    return (
        "Please apply an outage goodwill credit — I do not need a full billing policy review."
    )


def _msg3(store_t47):
    meta = store_t47.seed_meta
    return f"Did you check whether there is an outage near postcode {meta['postcode']}?"


def _msg4(store_t47):
    return "What about the duplicate charge — is that real?"


def _msg5(store_t47):
    return "Just fix the signal issue first if you have to choose."


_T47_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call("check_outage"),
]


@ek.scenario(
    agent_fixture="task_agent_t47",
    repeats=1,
    tags=("telecom", "task:T47", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t47_full(s, store_t47):
    (
        s.user_message(_msg1(store_t47))
        .user_message(_msg2(store_t47))
        .user_message(_msg3(store_t47))
        .user_message(_msg4(store_t47))
        .user_message(_msg5(store_t47))
        .assert_tool_calls(_T47_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_no_credit_rows(store_t47))
        .assert_output(m.string(min_len=5))
    )


@ek.scenario(
    agent_fixture="task_agent_t47",
    repeats=1,
    tags=("telecom", "task:T47", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t47_trace(s, store_t47):
    (
        s.user_message(_msg1(store_t47))
        .user_message(_msg2(store_t47))
        .user_message(_msg3(store_t47))
        .user_message(_msg4(store_t47))
        .user_message(_msg5(store_t47))
        .assert_tool_calls(_T47_TRACE, ordered=True, allow_extras=True)
    )


@ek.scenario(
    agent_fixture="task_agent_t47",
    repeats=1,
    tags=("telecom", "task:T47", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t47_state(s, store_t47):
    (
        s.user_message(_msg1(store_t47))
        .user_message(_msg2(store_t47))
        .user_message(_msg3(store_t47))
        .user_message(_msg4(store_t47))
        .user_message(_msg5(store_t47))
        .assert_that(lambda: o.assert_no_credit_rows(store_t47))
    )


@ek.scenario(
    agent_fixture="task_agent_t47",
    repeats=1,
    tags=("telecom", "task:T47", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t47_output(s, store_t47):
    (
        s.user_message(_msg1(store_t47))
        .user_message(_msg2(store_t47))
        .user_message(_msg3(store_t47))
        .user_message(_msg4(store_t47))
        .user_message(_msg5(store_t47))
        .assert_output(m.string(min_len=5))
    )
