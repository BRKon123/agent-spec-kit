"""Task T04 scenarios (explicit scripted messages and checks)."""

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
async def store_t04():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T04")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t04(store_t04):
    yield wrap_reference_agent(store_t04)


def _msg1(store_t04):
    meta = store_t04.seed_meta
    return (
        f"My mobile data's been dead all day on line {meta['line_id']}. "
        f"Account {meta['customer_id']}, verification token {meta['verification_token']}."
    )


def _msg2(store_t04):
    meta = store_t04.seed_meta
    return (
        f"I restarted my phone like you asked — still no data on {meta['line_id']}. "
        f"Can you log that and open a support ticket? "
        f"Account {meta['customer_id']}, verification token {meta['verification_token']}."
    )


_T04_TRACE = [
    m.tool_call("record_user_action"),
    m.tool_call("create_support_ticket"),
]

_T04_OUTPUT = m.llm_criteria(
    criteria=[
        "Confirms a support ticket was created or gives a ticket reference",
    ],
    threshold=1,
    model="openai:gpt-5-nano",
)


@ek.scenario(
    agent_fixture="task_agent_t04",
    repeats=1,
    tags=("telecom", "task:T04", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t04_full(s, store_t04):
    (
        s.user_message(_msg1(store_t04))
        .user_message(_msg2(store_t04))
        .assert_tool_calls(_T04_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_ticket_exists(store_t04))
        .assert_output(_T04_OUTPUT)
    )


@ek.scenario(
    agent_fixture="task_agent_t04",
    repeats=1,
    tags=("telecom", "task:T04", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t04_trace(s, store_t04):
    (
        s.user_message(_msg1(store_t04))
        .user_message(_msg2(store_t04))
        .assert_tool_calls(_T04_TRACE, ordered=True, allow_extras=True)
    )


@ek.scenario(
    agent_fixture="task_agent_t04",
    repeats=1,
    tags=("telecom", "task:T04", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t04_state(s, store_t04):
    (
        s.user_message(_msg1(store_t04))
        .user_message(_msg2(store_t04))
        .assert_that(lambda: o.assert_ticket_exists(store_t04))
    )


@ek.scenario(
    agent_fixture="task_agent_t04",
    repeats=1,
    tags=("telecom", "task:T04", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t04_output(s, store_t04):
    (
        s.user_message(_msg1(store_t04))
        .user_message(_msg2(store_t04))
        .assert_output(_T04_OUTPUT)
    )
