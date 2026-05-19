"""Task T29 scenarios (explicit scripted messages and checks)."""

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
async def store_t29():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T29")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t29(store_t29):
    yield wrap_reference_agent(store_t29)


def _msg1(store_t29):
    return "Hi — I need a replacement SIM for my other line, the one ending 9999."


def _msg2(store_t29):
    return "Sorry, that's not right — I meant my main line, not that one."


def _msg3(store_t29):
    meta = store_t29.seed_meta
    return (
        f"Yes please — ship the replacement to my default address for line {meta['line_id']}. "
        f"Account {meta['customer_id']}, verification token {meta['verification_token']}."
    )


_T29_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call("order_replacement_sim"),
]


@ek.scenario(
    agent_fixture="task_agent_t29",
    repeats=1,
    tags=("telecom", "task:T29", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t29_full(s, store_t29):
    (
        s.user_message(_msg1(store_t29))
        .user_message(_msg2(store_t29))
        .user_message(_msg3(store_t29))
        .assert_tool_calls(_T29_TRACE, ordered=True, allow_extras=True)
        .assert_that(
            lambda: o.assert_sim_order_for_line(store_t29, store_t29.seed_meta["line_id"])
        )
    )


@ek.scenario(
    agent_fixture="task_agent_t29",
    repeats=1,
    tags=("telecom", "task:T29", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t29_trace(s, store_t29):
    (
        s.user_message(_msg1(store_t29))
        .user_message(_msg2(store_t29))
        .user_message(_msg3(store_t29))
        .assert_tool_calls([m.tool_call("authenticate_customer")], ordered=True, allow_extras=True)
    )


@ek.scenario(
    agent_fixture="task_agent_t29",
    repeats=1,
    tags=("telecom", "task:T29", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t29_state(s, store_t29):
    (
        s.user_message(_msg1(store_t29))
        .user_message(_msg2(store_t29))
        .user_message(_msg3(store_t29))
        .assert_that(
            lambda: o.assert_sim_order_for_line(store_t29, store_t29.seed_meta["line_id"])
        )
    )


@ek.scenario(
    agent_fixture="task_agent_t29",
    repeats=1,
    tags=("telecom", "task:T29", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t29_output(s, store_t29):
    (
        s.user_message(_msg1(store_t29))
        .user_message(_msg2(store_t29))
        .user_message(_msg3(store_t29))
        .assert_output(m.string(min_len=5))
    )
