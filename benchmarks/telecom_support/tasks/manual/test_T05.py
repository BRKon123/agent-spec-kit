"""Task T05 scenarios (explicit scripted messages and checks)."""

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
async def store_t05():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T05")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t05(store_t05):
    yield wrap_reference_agent(store_t05)


def _msg(store_t05):
    meta = store_t05.seed_meta
    return (
        f"Intermittent latency spikes on my line; not sure if outage or device."
        f" Customer {meta['customer_id']}, verification {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )


_T05_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call("run_network_diagnostics_specialist"),
]

_T05_OUTPUT = m.one_of(
    m.contains("latency"),
    m.contains("spike"),
    m.contains("congestion"),
    m.contains("diagnostic"),
    m.contains("network"),
)


@ek.scenario(
    agent_fixture="task_agent_t05",
    repeats=1,
    tags=("telecom", "task:T05", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t05_full(s, store_t05):
    (
        s.user_message(_msg(store_t05))
        .assert_tool_calls(_T05_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_no_credit_rows(store_t05))
        .assert_output(_T05_OUTPUT)
    )


@ek.scenario(
    agent_fixture="task_agent_t05",
    repeats=1,
    tags=("telecom", "task:T05", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t05_trace(s, store_t05):
    (s.user_message(_msg(store_t05)).assert_tool_calls(_T05_TRACE, ordered=True, allow_extras=True))


@ek.scenario(
    agent_fixture="task_agent_t05",
    repeats=1,
    tags=("telecom", "task:T05", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t05_state(s, store_t05):
    (s.user_message(_msg(store_t05)).assert_that(lambda: o.assert_no_credit_rows(store_t05)))


@ek.scenario(
    agent_fixture="task_agent_t05",
    repeats=1,
    tags=("telecom", "task:T05", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t05_output(s, store_t05):
    (s.user_message(_msg(store_t05)).assert_output(_T05_OUTPUT))
