"""Task T48 scenarios (explicit scripted messages and checks)."""

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
async def store_t48():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T48")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t48(store_t48):
    yield wrap_reference_agent(store_t48)


def _msg(store_t48):
    meta = store_t48.seed_meta
    return (
        f"I need to speak to a supervisor right now — do not troubleshoot or ask me to "
        f"restart my phone. Please escalate without opening any tickets in your system."
        f" Customer {meta['customer_id']}, verification {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )



@ek.scenario(
    agent_fixture="task_agent_t48",
    repeats=2,
    tags=("telecom", "task:T48", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t48_full(s, store_t48):
    meta = store_t48.seed_meta
    (
            s.user_message(_msg(store_t48))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_no_tickets(store_t48))
            .assert_output(
                m.one_of(
                    m.contains("troubleshoot"),
                    m.contains("restart"),
                    m.contains("escalat"),
                    m.contains("policy"),
                )
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t48",
    repeats=2,
    tags=("telecom", "task:T48", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t48_trace(s, store_t48):
    meta = store_t48.seed_meta
    (
            s.user_message(_msg(store_t48))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                ],
                ordered=True,
                allow_extras=True,
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t48",
    repeats=2,
    tags=("telecom", "task:T48", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t48_state(s, store_t48):
    meta = store_t48.seed_meta
    (
            s.user_message(_msg(store_t48))
            .assert_that(lambda: o.assert_no_tickets(store_t48))
        )


@ek.scenario(
    agent_fixture="task_agent_t48",
    repeats=2,
    tags=("telecom", "task:T48", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t48_output(s, store_t48):
    meta = store_t48.seed_meta
    (
            s.user_message(_msg(store_t48))
            .assert_output(
                m.one_of(
                    m.contains("troubleshoot"),
                    m.contains("restart"),
                    m.contains("escalat"),
                    m.contains("policy"),
                )
            )
        )
