"""Task T31 scenarios (explicit scripted messages and checks)."""

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
async def store_t31():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T31")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t31(store_t31):
    yield wrap_reference_agent(store_t31)


def _msg(store_t31):
    meta = store_t31.seed_meta
    return (
        f"My phone won't take eSIM any more but I still need a replacement eSIM on my line — "
        f"can you arrange that without checking device compatibility?"
        f" Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )


_T31_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call("get_customer_profile"),
    m.tool_call(
        "order_replacement_sim",
        args=m.object({"sim_type": m.one_of("esim")}, extra="forbid"),
    ),
]

_T31_OUTPUT = m.string(min_len=5)


@ek.scenario(
    agent_fixture="task_agent_t31",
    repeats=1,
    tags=("telecom", "task:T31", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t31_full(s, store_t31):
    (
        s.user_message(_msg(store_t31))
        .assert_tool_calls(
            [
                m.tool_call("authenticate_customer"),
                m.tool_call("get_customer_profile"),
            ],
            ordered=True,
            allow_extras=True,
        )
        .assert_that(lambda: o.assert_no_sim_orders(store_t31))
        .assert_output(_T31_OUTPUT)
    )


@ek.scenario(
    agent_fixture="task_agent_t31",
    repeats=1,
    tags=("telecom", "task:T31", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t31_trace(s, store_t31):
    (
        s.user_message(_msg(store_t31))
        .assert_tool_calls(_T31_TRACE, ordered=True, allow_extras=True)
    )


@ek.scenario(
    agent_fixture="task_agent_t31",
    repeats=1,
    tags=("telecom", "task:T31", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t31_state(s, store_t31):
    (
        s.user_message(_msg(store_t31))
        .assert_that(lambda: o.assert_no_sim_orders(store_t31))
    )


@ek.scenario(
    agent_fixture="task_agent_t31",
    repeats=1,
    tags=("telecom", "task:T31", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t31_output(s, store_t31):
    (
        s.user_message(_msg(store_t31))
        .assert_output(_T31_OUTPUT)
    )
