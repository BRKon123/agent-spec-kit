"""Task T43 scenarios (explicit scripted messages and checks)."""

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
async def store_t43():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T43")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t43(store_t43):
    yield wrap_reference_agent(store_t43)


def _msg1(_store_t43):
    return "I need a replacement SIM — the problem is on my main number ending 4421."


def _msg2(store_t43):
    meta = store_t43.seed_meta
    return (
        f"Wait, sorry — I meant our family line ending 7788, not 4421. "
        f"The correct line id is {meta['line_id']}."
    )


def _msg3(store_t43):
    meta = store_t43.seed_meta
    return (
        f"Yes — {meta['line_id']} is the right line. Please just confirm status for now; "
        f"do not ship a replacement SIM yet."
        f" Account {meta['customer_id']}, verification token {meta['verification_token']}."
    )


_T43_TRACE = [m.tool_call("authenticate_customer")]


def _dialogue(s, store_t43):
    return (
        s.user_message(_msg1(store_t43))
        .user_message(_msg2(store_t43))
        .user_message(_msg3(store_t43))
    )


@ek.scenario(
    agent_fixture="task_agent_t43",
    repeats=1,
    tags=("telecom", "task:T43", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t43_full(s, store_t43):
    (
        _dialogue(s, store_t43)
        .assert_tool_calls(_T43_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_no_mutations(store_t43))
        .assert_output(m.string(min_len=5))
    )


@ek.scenario(
    agent_fixture="task_agent_t43",
    repeats=1,
    tags=("telecom", "task:T43", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t43_trace(s, store_t43):
    (_dialogue(s, store_t43).assert_tool_calls(_T43_TRACE, ordered=True, allow_extras=True))


@ek.scenario(
    agent_fixture="task_agent_t43",
    repeats=1,
    tags=("telecom", "task:T43", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t43_state(s, store_t43):
    (_dialogue(s, store_t43).assert_that(lambda: o.assert_no_mutations(store_t43)))


@ek.scenario(
    agent_fixture="task_agent_t43",
    repeats=1,
    tags=("telecom", "task:T43", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t43_output(s, store_t43):
    (_dialogue(s, store_t43).assert_output(m.string(min_len=5)))
