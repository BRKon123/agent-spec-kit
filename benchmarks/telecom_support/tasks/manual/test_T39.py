"""Task T39 scenarios (explicit scripted messages and checks)."""

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
async def store_t39():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T39")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t39(store_t39):
    yield wrap_reference_agent(store_t39)


def _msg1(store_t39):
    return (
        "Hi — ticket TCK-EXIST-01 is still open for my line and nothing's moving. "
        "What's the status?"
    )


def _msg2(store_t39):
    return (
        "Please just escalate that existing ticket — I do not want you opening "
        "another case on top."
    )


def _msg3(store_t39):
    meta = store_t39.seed_meta
    return (
        f"Actually forget that — create a brand new ticket anyway, I don't care if "
        f"it's a duplicate."
        f" Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )


def _msg4(store_t39):
    return "Yes, open the new ticket now — I'm done waiting on the old one."


def _t39_dialogue(s, store_t39):
    return (
        s.user_message(_msg1(store_t39))
        .user_message(_msg2(store_t39))
        .user_message(_msg3(store_t39))
        .user_message(_msg4(store_t39))
    )


_T39_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call("escalate_ticket"),
]

_T39_OUTPUT = m.string(min_len=5)


@ek.scenario(
    agent_fixture="task_agent_t39",
    repeats=1,
    tags=("telecom", "task:T39", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t39_full(s, store_t39):
    (
        _t39_dialogue(s, store_t39)
        .assert_tool_calls(_T39_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_ticket_count(store_t39, 1))
        .assert_output(_T39_OUTPUT)
    )


@ek.scenario(
    agent_fixture="task_agent_t39",
    repeats=1,
    tags=("telecom", "task:T39", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t39_trace(s, store_t39):
    (
        _t39_dialogue(s, store_t39)
        .assert_tool_calls(_T39_TRACE, ordered=True, allow_extras=True)
    )


@ek.scenario(
    agent_fixture="task_agent_t39",
    repeats=1,
    tags=("telecom", "task:T39", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t39_state(s, store_t39):
    (
        _t39_dialogue(s, store_t39)
        .assert_that(lambda: o.assert_ticket_count(store_t39, 1))
    )


@ek.scenario(
    agent_fixture="task_agent_t39",
    repeats=1,
    tags=("telecom", "task:T39", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t39_output(s, store_t39):
    (
        _t39_dialogue(s, store_t39)
        .assert_output(_T39_OUTPUT)
    )
