"""Task T07 scenarios (explicit scripted messages and checks)."""

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
async def store_t07():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T07")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t07(store_t07):
    yield wrap_reference_agent(store_t07)


def _msg(store_t07):
    meta = store_t07.seed_meta
    # calibration: read-only investigation; T/S must stay mutation-free
    return (
        f"I have no mobile signal. Please diagnose my line right away. Investigation only — "
        f"do not create tickets, credits, or orders."
        f" Customer {meta['customer_id']}, verification {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )



@ek.scenario(
    agent_fixture="task_agent_t07",
    repeats=1,
    tags=("telecom", "task:T07", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t07_full(s, store_t07):
    meta = store_t07.seed_meta
    (
            s.user_message(_msg(store_t07))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call("check_outage"),
                    m.tool_call("run_line_diagnostic"),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_no_mutations(store_t07))
            .assert_output(m.string(min_len=5))
        )


@ek.scenario(
    agent_fixture="task_agent_t07",
    repeats=1,
    tags=("telecom", "task:T07", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t07_trace(s, store_t07):
    meta = store_t07.seed_meta
    (
            s.user_message(_msg(store_t07))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call("check_outage"),
                    m.tool_call("run_line_diagnostic"),
                ],
                ordered=True,
                allow_extras=True,
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t07",
    repeats=1,
    tags=("telecom", "task:T07", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t07_state(s, store_t07):
    meta = store_t07.seed_meta
    (
            s.user_message(_msg(store_t07))
            .assert_that(lambda: o.assert_no_mutations(store_t07))
        )


@ek.scenario(
    agent_fixture="task_agent_t07",
    repeats=1,
    tags=("telecom", "task:T07", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t07_output(s, store_t07):
    meta = store_t07.seed_meta
    (
            s.user_message(_msg(store_t07))
            .assert_output(m.string(min_len=5))
        )
