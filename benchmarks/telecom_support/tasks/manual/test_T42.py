"""Task T42 scenarios (explicit scripted messages and checks)."""

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
async def store_t42():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T42")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t42(store_t42):
    yield wrap_reference_agent(store_t42)


def _msg1(_store_t42):
    return "My mobile data is not working at all today."


def _msg2(_store_t42):
    return (
        "Sorry, ignore the data thing for a moment — I actually lost my SIM card. "
        "Can you check whether my line is still active? Please do not order a replacement yet."
    )


def _msg3(store_t42):
    meta = store_t42.seed_meta
    return (
        f"Yes, still the lost SIM — check line status only. Do not order or ship a "
        f"replacement SIM. Account {meta['customer_id']}, verification token "
        f"{meta['verification_token']}, line {meta['line_id']}."
    )


_T42_TRACE = [m.tool_call("authenticate_customer")]


def _dialogue(s, store_t42):
    return s.user_message(_msg1(store_t42)).user_message(_msg2(store_t42)).user_message(_msg3(store_t42))


@ek.scenario(
    agent_fixture="task_agent_t42",
    repeats=1,
    tags=("telecom", "task:T42", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t42_full(s, store_t42):
    (
        _dialogue(s, store_t42)
        .assert_tool_calls(_T42_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_no_mutations(store_t42))
        .assert_output(m.string(min_len=5))
    )


@ek.scenario(
    agent_fixture="task_agent_t42",
    repeats=1,
    tags=("telecom", "task:T42", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t42_trace(s, store_t42):
    (_dialogue(s, store_t42).assert_tool_calls(_T42_TRACE, ordered=True, allow_extras=True))


@ek.scenario(
    agent_fixture="task_agent_t42",
    repeats=1,
    tags=("telecom", "task:T42", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t42_state(s, store_t42):
    (_dialogue(s, store_t42).assert_that(lambda: o.assert_no_mutations(store_t42)))


@ek.scenario(
    agent_fixture="task_agent_t42",
    repeats=1,
    tags=("telecom", "task:T42", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t42_output(s, store_t42):
    (_dialogue(s, store_t42).assert_output(m.string(min_len=5)))
