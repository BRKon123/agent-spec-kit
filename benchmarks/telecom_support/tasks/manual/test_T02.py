"""Task T02 scenarios (explicit scripted messages and checks)."""

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
async def store_t02():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T02")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t02(store_t02):
    yield wrap_reference_agent(store_t02)


def _msg(store_t02):
    meta = store_t02.seed_meta
    return (
        f"No mobile data at home since this morning — neighbours said there might be an outage "
        f"around {meta['postcode']}. Is that what's going on? "
        f"Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )


_T02_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call("check_outage"),
]


def _t02_output(store_t02):
    meta = store_t02.seed_meta
    return m.llm_criteria(
        criteria=[
            "Explains whether a network outage affects the customer's service",
            f"Mentions postcode {meta['postcode']} or the customer's stated area",
        ],
        threshold=2,
        model="openai:gpt-5-nano",
    )


@ek.scenario(
    agent_fixture="task_agent_t02",
    repeats=1,
    tags=("telecom", "task:T02", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t02_full(s, store_t02):
    (
        s.user_message(_msg(store_t02))
        .assert_tool_calls(_T02_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_no_sim_orders(store_t02))
        .assert_that(lambda: o.assert_no_tickets(store_t02))
        .assert_that(lambda: o.assert_no_credit_rows(store_t02))
        .assert_output(_t02_output(store_t02))
    )


@ek.scenario(
    agent_fixture="task_agent_t02",
    repeats=1,
    tags=("telecom", "task:T02", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t02_trace(s, store_t02):
    (s.user_message(_msg(store_t02)).assert_tool_calls(_T02_TRACE, ordered=True, allow_extras=True))


@ek.scenario(
    agent_fixture="task_agent_t02",
    repeats=1,
    tags=("telecom", "task:T02", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t02_state(s, store_t02):
    (
        s.user_message(_msg(store_t02))
        .assert_that(lambda: o.assert_no_sim_orders(store_t02))
        .assert_that(lambda: o.assert_no_tickets(store_t02))
        .assert_that(lambda: o.assert_no_credit_rows(store_t02))
    )


@ek.scenario(
    agent_fixture="task_agent_t02",
    repeats=1,
    tags=("telecom", "task:T02", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t02_output(s, store_t02):
    (s.user_message(_msg(store_t02)).assert_output(_t02_output(store_t02)))
