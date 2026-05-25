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
from tasks.specs import trace_oracles as to

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
    return "Hi — I need a replacement SIM. Pretty sure it's for line LINE-WRONG on my account."


def _msg2(store_t29):
    meta = store_t29.seed_meta
    return (
        f"Sorry, wrong line — it's {meta['line_id']}. Account {meta['customer_id']}, "
        f"verification token {meta['verification_token']}. Please ship a replacement to my "
        f"default address now."
    )


def _msg3(store_t29):
    return "Thanks — go ahead with that order."


_T29_AUTH_TRACE = [m.tool_call("authenticate_customer")]

def _seed_line(store_t29) -> str:
    return str(store_t29.seed_meta["line_id"])


def _t29_order_trace(store_t29):
    return [
        m.tool_call("authenticate_customer"),
        to.order_sim_on_line(_seed_line(store_t29)),
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
        .assert_tool_calls(_t29_order_trace(store_t29), ordered=True, allow_extras=True)
        .user_message(_msg3(store_t29))
        .assert_that(lambda: o.assert_sim_orders_only_on_seed_line(store_t29))
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
        .assert_tool_calls(_T29_AUTH_TRACE, ordered=True, allow_extras=True)
        .user_message(_msg3(store_t29))
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
        .assert_that(lambda: o.assert_sim_orders_only_on_seed_line(store_t29))
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
