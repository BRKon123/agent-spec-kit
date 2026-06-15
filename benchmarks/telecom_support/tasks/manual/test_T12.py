"""Task T12 scenarios (explicit scripted messages and checks)."""

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
async def store_t12():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T12")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t12(store_t12):
    yield wrap_reference_agent(store_t12)


def _msg(store_t12):
    meta = store_t12.seed_meta
    return (
        f"Flying to the US next week — not sure if my plan covers it or what roaming costs look like. "
        f"Can you check plan {meta.get('plan_id', 'PLAN-STD')} and walk me through the limits? "
        f"Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )


_T12_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call("get_plan_details"),
]

_T12_OUTPUT = m.llm_criteria(
    criteria=[
        "Explains whether the plan covers the US or roaming for that destination",
        "Mentions plan limits, roaming rules, or add-ons in customer-friendly language",
    ],
    threshold=2,
    model="openai:gpt-5-nano",
)


@ek.scenario(
    agent_fixture="task_agent_t12",
    repeats=1,
    tags=("telecom", "task:T12", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t12_full(s, store_t12):
    (
        s.user_message(_msg(store_t12))
        .assert_tool_calls(_T12_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_no_credit_rows(store_t12))
        .assert_output(_T12_OUTPUT)
    )


@ek.scenario(
    agent_fixture="task_agent_t12",
    repeats=1,
    tags=("telecom", "task:T12", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t12_trace(s, store_t12):
    (s.user_message(_msg(store_t12)).assert_tool_calls(_T12_TRACE, ordered=True, allow_extras=True))


@ek.scenario(
    agent_fixture="task_agent_t12",
    repeats=1,
    tags=("telecom", "task:T12", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t12_state(s, store_t12):
    (s.user_message(_msg(store_t12)).assert_that(lambda: o.assert_no_credit_rows(store_t12)))


@ek.scenario(
    agent_fixture="task_agent_t12",
    repeats=1,
    tags=("telecom", "task:T12", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t12_output(s, store_t12):
    (s.user_message(_msg(store_t12)).assert_output(_T12_OUTPUT))
