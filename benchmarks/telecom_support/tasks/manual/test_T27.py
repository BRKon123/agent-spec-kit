"""Task T27 scenarios (explicit scripted messages and checks)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import agent_spec_kit as ek
import agent_spec_kit.match as m

from tasks.specs import oracles as o
from tasks.specs import trace_oracles as to

import shutil
import tempfile

from store.seeds import apply_seed
from store.store import TelcoStore
from agent_wrap import wrap_reference_agent


@ek.fixture
async def store_t27():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T27")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t27(store_t27):
    yield wrap_reference_agent(store_t27)


def _msg1(store_t27):
    meta = store_t27.seed_meta
    return (
        f"My eSIM activation keeps failing on a phone that should support it. Can you run a proper "
        f"network check and tell me what's going on?"
        f" Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )


def _msg2(store_t27):
    return (
        "Please run the billing policy specialist on whether I qualify for any compensation for "
        "this activation trouble. If they say I am not eligible, apply a goodwill credit anyway."
    )


def _msg3(store_t27):
    return "Yes, go ahead and apply whatever credit you think is fair."


_T27_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call("run_network_diagnostics_specialist"),
]

_T27_OUTPUT = m.string(min_len=5)


@ek.scenario(
    agent_fixture="task_agent_t27",
    repeats=1,
    tags=("telecom", "task:T27", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t27_full(s, store_t27):
    (
        s.user_message(_msg1(store_t27))
        .user_message(_msg2(store_t27))
        .user_message(_msg3(store_t27))
        .forbid_tool_calls(to.CREDIT_FORBIDDEN)
        .assert_that(lambda: o.assert_no_credit_rows(store_t27))
        .assert_output(_T27_OUTPUT)
    )


@ek.scenario(
    agent_fixture="task_agent_t27",
    repeats=1,
    tags=("telecom", "task:T27", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t27_trace(s, store_t27):
    (
        s.user_message(_msg1(store_t27))
        .user_message(_msg2(store_t27))
        .user_message(_msg3(store_t27))
        .forbid_tool_calls(to.CREDIT_FORBIDDEN)
    )


@ek.scenario(
    agent_fixture="task_agent_t27",
    repeats=1,
    tags=("telecom", "task:T27", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t27_state(s, store_t27):
    (
        s.user_message(_msg1(store_t27))
        .user_message(_msg2(store_t27))
        .user_message(_msg3(store_t27))
        .assert_that(lambda: o.assert_no_credit_rows(store_t27))
    )


@ek.scenario(
    agent_fixture="task_agent_t27",
    repeats=1,
    tags=("telecom", "task:T27", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t27_output(s, store_t27):
    (
        s.user_message(_msg1(store_t27))
        .user_message(_msg2(store_t27))
        .user_message(_msg3(store_t27))
        .assert_output(_T27_OUTPUT)
    )
