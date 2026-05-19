"""Task T01 scenarios (explicit scripted messages and checks)."""

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
async def store_t01():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T01")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t01(store_t01):
    yield wrap_reference_agent(store_t01)


def _msg(store_t01):
    meta = store_t01.seed_meta
    return (
        f"My mobile data isn't working at all — can you check whether data is turned on "
        f"for line {meta['line_id']}? "
        f"Account {meta['customer_id']}, verification token {meta['verification_token']}."
    )


_T01_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call(
        "get_line_status",
        args=m.object({"line_id": m.string()}),
    ),
]

_T01_OUTPUT = m.llm_criteria(
    criteria=[
        "Explains whether mobile data is enabled or disabled on the customer's line",
        "Addresses the customer's mobile data connectivity problem",
    ],
    threshold=2,
    model="openai:gpt-5-nano",
)


@ek.scenario(
    agent_fixture="task_agent_t01",
    repeats=1,
    tags=("telecom", "task:T01", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t01_full(s, store_t01):
    (
        s.user_message(_msg(store_t01))
        .assert_tool_calls(_T01_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_no_mutations(store_t01))
        .assert_output(_T01_OUTPUT)
    )


@ek.scenario(
    agent_fixture="task_agent_t01",
    repeats=1,
    tags=("telecom", "task:T01", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t01_trace(s, store_t01):
    (s.user_message(_msg(store_t01)).assert_tool_calls(_T01_TRACE, ordered=True, allow_extras=True))


@ek.scenario(
    agent_fixture="task_agent_t01",
    repeats=1,
    tags=("telecom", "task:T01", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t01_state(s, store_t01):
    (s.user_message(_msg(store_t01)).assert_that(lambda: o.assert_no_mutations(store_t01)))


@ek.scenario(
    agent_fixture="task_agent_t01",
    repeats=1,
    tags=("telecom", "task:T01", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t01_output(s, store_t01):
    (s.user_message(_msg(store_t01)).assert_output(_T01_OUTPUT))
