"""Task T34 scenarios (explicit scripted messages and checks)."""

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
async def store_t34():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T34")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t34(store_t34):
    yield wrap_reference_agent(store_t34)


def _msg(store_t34):
    meta = store_t34.seed_meta
    return (
        f"I need to book a store appointment. Please diagnose my line and schedule a store "
        f"visit in the same response."
        f" Customer {meta['customer_id']}, verification {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )



@ek.scenario(
    agent_fixture="task_agent_t34",
    repeats=1,
    tags=("telecom", "task:T34", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t34_full(s, store_t34):
    meta = store_t34.seed_meta
    (
            s.user_message(_msg(store_t34))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call("run_line_diagnostic"),
                    m.tool_call("schedule_store_appointment"),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_appointment_exists(store_t34))
            .assert_output(m.contains("appointment"))
        )


@ek.scenario(
    agent_fixture="task_agent_t34",
    repeats=1,
    tags=("telecom", "task:T34", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t34_trace(s, store_t34):
    meta = store_t34.seed_meta
    (
            s.user_message(_msg(store_t34))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call("run_line_diagnostic"),
                    m.tool_call("schedule_store_appointment"),
                ],
                ordered=True,
                allow_extras=True,
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t34",
    repeats=1,
    tags=("telecom", "task:T34", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t34_state(s, store_t34):
    meta = store_t34.seed_meta
    (
            s.user_message(_msg(store_t34))
            .assert_that(lambda: o.assert_appointment_exists(store_t34))
        )


@ek.scenario(
    agent_fixture="task_agent_t34",
    repeats=1,
    tags=("telecom", "task:T34", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t34_output(s, store_t34):
    meta = store_t34.seed_meta
    (
            s.user_message(_msg(store_t34))
            .assert_output(m.contains("appointment"))
        )
