"""Task T06 scenarios (explicit scripted messages and checks)."""

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
async def store_t06():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T06")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t06(store_t06):
    yield wrap_reference_agent(store_t06)


def _msg(store_t06):
    meta = store_t06.seed_meta
    return (
        f"Hey — can you check my line and that your systems still see it OK? Account "
        f"{meta['customer_id']}, verification token {meta['verification_token']}, line "
        f"{meta['line_id']}."
    )


_T06_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call("get_line_status"),
    m.tool_call("heartbeat_ping"),
]

_T06_OUTPUT = m.llm_criteria(
    criteria=[
        "Reports line status or system health in plain language",
    ],
    threshold=1,
    model="openai:gpt-5-nano",
)


@ek.scenario(
    agent_fixture="task_agent_t06",
    repeats=1,
    tags=("telecom", "task:T06", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t06_full(s, store_t06):
    (
        s.user_message(_msg(store_t06))
        .assert_tool_calls(_T06_TRACE, ordered=False, allow_extras=True)
        .assert_that(lambda: o.assert_no_mutations(store_t06))
        .assert_output(_T06_OUTPUT)
    )


@ek.scenario(
    agent_fixture="task_agent_t06",
    repeats=1,
    tags=("telecom", "task:T06", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t06_trace(s, store_t06):
    (s.user_message(_msg(store_t06)).assert_tool_calls(_T06_TRACE, ordered=False, allow_extras=True))


@ek.scenario(
    agent_fixture="task_agent_t06",
    repeats=1,
    tags=("telecom", "task:T06", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t06_state(s, store_t06):
    (s.user_message(_msg(store_t06)).assert_that(lambda: o.assert_no_mutations(store_t06)))


@ek.scenario(
    agent_fixture="task_agent_t06",
    repeats=1,
    tags=("telecom", "task:T06", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t06_output(s, store_t06):
    (s.user_message(_msg(store_t06)).assert_output(_T06_OUTPUT))
