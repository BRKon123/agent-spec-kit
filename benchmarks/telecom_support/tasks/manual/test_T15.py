"""Task T15 scenarios (explicit scripted messages and checks)."""

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
async def store_t15():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T15")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t15(store_t15):
    yield wrap_reference_agent(store_t15)


def _msg(store_t15):
    meta = store_t15.seed_meta
    return (
        f"I'm travelling and mobile data died right after I crossed the border. "
        f"Could it be an outage back home? My postcode is {meta['postcode']}. "
        f"Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )


_T15_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call("get_plan_details"),
    m.tool_call("get_line_status"),
]

_T15_OUTPUT = m.one_of(
    m.llm_criteria(
        criteria=[
            "Discusses roaming or mobile data while the customer is abroad",
            "Mentions outage, plan, or line status in plain language",
        ],
        threshold=2,
        model="openai:gpt-5-nano",
    ),
    m.contains("outage"),
    m.contains("roaming"),
    m.contains("plan"),
)


@ek.scenario(
    agent_fixture="task_agent_t15",
    repeats=1,
    tags=("telecom", "task:T15", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t15_full(s, store_t15):
    (
        s.user_message(_msg(store_t15))
        .assert_tool_calls(_T15_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_no_credit_rows(store_t15))
        .assert_output(_T15_OUTPUT)
    )


@ek.scenario(
    agent_fixture="task_agent_t15",
    repeats=1,
    tags=("telecom", "task:T15", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t15_trace(s, store_t15):
    (s.user_message(_msg(store_t15)).assert_tool_calls(_T15_TRACE, ordered=True, allow_extras=True))


@ek.scenario(
    agent_fixture="task_agent_t15",
    repeats=1,
    tags=("telecom", "task:T15", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t15_state(s, store_t15):
    (s.user_message(_msg(store_t15)).assert_that(lambda: o.assert_no_credit_rows(store_t15)))


@ek.scenario(
    agent_fixture="task_agent_t15",
    repeats=1,
    tags=("telecom", "task:T15", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t15_output(s, store_t15):
    (s.user_message(_msg(store_t15)).assert_output(_T15_OUTPUT))
