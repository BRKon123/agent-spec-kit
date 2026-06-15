"""Task T11 scenarios (explicit scripted messages and checks)."""

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
async def store_t11():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T11")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t11(store_t11):
    yield wrap_reference_agent(store_t11)


def _msg(store_t11):
    meta = store_t11.seed_meta
    return (
        f"I'm abroad and mobile data just stopped working — could roaming be turned off on my line? "
        f"Can you check my plan and line status? I don't need a ticket yet, just want to know what's up. "
        f"Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )


_T11_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call("get_line_status"),
    m.tool_call("get_plan_details"),
]


@ek.scenario(
    agent_fixture="task_agent_t11",
    repeats=1,
    tags=("telecom", "task:T11", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t11_full(s, store_t11):
    (
            s.user_message(_msg(store_t11))
            .assert_tool_calls(_T11_TRACE, ordered=True, allow_extras=True)
            .assert_that(lambda: o.assert_no_tickets(store_t11))
            .assert_output(m.contains("plan"))
        )


@ek.scenario(
    agent_fixture="task_agent_t11",
    repeats=1,
    tags=("telecom", "task:T11", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t11_trace(s, store_t11):
    (
            s.user_message(_msg(store_t11))
            .assert_tool_calls(_T11_TRACE, ordered=True, allow_extras=True)
        )


@ek.scenario(
    agent_fixture="task_agent_t11",
    repeats=1,
    tags=("telecom", "task:T11", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t11_state(s, store_t11):
    (
        s.user_message(_msg1(store_t11))
        .user_message(_msg2(store_t11))
        .assert_that(lambda: o.assert_no_tickets(store_t11))
    )


@ek.scenario(
    agent_fixture="task_agent_t11",
    repeats=1,
    tags=("telecom", "task:T11", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t11_output(s, store_t11):
    (
        s.user_message(_msg1(store_t11))
        .user_message(_msg2(store_t11))
        .assert_output(_T11_OUTPUT)
    )
