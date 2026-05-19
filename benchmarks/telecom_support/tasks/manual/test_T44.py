"""Task T44 scenarios (explicit scripted messages and checks)."""

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
async def store_t44():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T44")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t44(store_t44):
    yield wrap_reference_agent(store_t44)


def _msg1(store_t44):
    meta = store_t44.seed_meta
    return (
        f"My mobile data still will not work and I need this sorted."
        f" Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}. Please authenticate and check the line only — do not send "
        f"restart or troubleshooting steps yet."
    )


def _msg2(store_t44):
    meta = store_t44.seed_meta
    return (
        f"Actually I have not restarted yet — I am waiting for an important call. "
        f"You already verified me above. Please send the official device restart step for "
        f"{meta['line_id']} — postcode {meta.get('postcode', 'E1 6AN')}."
    )


def _msg3(_store_t44):
    return (
        "I cannot restart right now. Please do not open a ticket yet — just tell me the step "
        "for when I am off the call."
    )


_T44_TRACE = [m.tool_call("send_troubleshooting_step")]

_T44_OUTPUT = m.one_of(
    m.contains("restart"),
    m.contains("power cycle"),
    m.contains("troubleshoot"),
    m.llm_criteria(
        criteria=[
            "Acknowledges the customer had not restarted yet or gives a concrete next step",
        ],
        threshold=1,
        model="openai:gpt-5-nano",
    ),
)


def _dialogue_through_contradiction(s, store_t44):
    return s.user_message(_msg1(store_t44)).user_message(_msg2(store_t44))


@ek.scenario(
    agent_fixture="task_agent_t44",
    repeats=1,
    tags=("telecom", "task:T44", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t44_full(s, store_t44):
    (
        _dialogue_through_contradiction(s, store_t44)
        .assert_tool_calls(_T44_TRACE, ordered=True, allow_extras=True)
        .user_message(_msg3(store_t44))
        .assert_that(lambda: o.assert_no_tickets(store_t44))
        .assert_output(_T44_OUTPUT)
    )


@ek.scenario(
    agent_fixture="task_agent_t44",
    repeats=1,
    tags=("telecom", "task:T44", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t44_trace(s, store_t44):
    (
        _dialogue_through_contradiction(s, store_t44)
        .assert_tool_calls(_T44_TRACE, ordered=True, allow_extras=True)
        .user_message(_msg3(store_t44))
    )


@ek.scenario(
    agent_fixture="task_agent_t44",
    repeats=1,
    tags=("telecom", "task:T44", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t44_state(s, store_t44):
    (
        _dialogue_through_contradiction(s, store_t44)
        .user_message(_msg3(store_t44))
        .assert_that(lambda: o.assert_no_tickets(store_t44))
    )


@ek.scenario(
    agent_fixture="task_agent_t44",
    repeats=1,
    tags=("telecom", "task:T44", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t44_output(s, store_t44):
    (
        _dialogue_through_contradiction(s, store_t44)
        .assert_output(_T44_OUTPUT)
        .user_message(_msg3(store_t44))
    )
