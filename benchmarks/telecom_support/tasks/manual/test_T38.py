"""Task T38 scenarios (explicit scripted messages and checks)."""

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
async def store_t38():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T38")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t38(store_t38):
    yield wrap_reference_agent(store_t38)


def _msg(store_t38):
    meta = store_t38.seed_meta
    return (
        f"I have intermittent latency on my line. Please run thorough network diagnostics "
        f"and confirm your systems are responsive."
        f" Customer {meta['customer_id']}, verification {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )



@ek.scenario(
    agent_fixture="task_agent_t38",
    repeats=2,
    tags=("telecom", "task:T38", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t38_full(s, store_t38):
    meta = store_t38.seed_meta
    (
            s.user_message(_msg(store_t38))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call("run_network_diagnostics_specialist"),
                    m.tool_call("heartbeat_ping"),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_no_mutations(store_t38))
            .assert_output(m.string(min_len=5))
        )


@ek.scenario(
    agent_fixture="task_agent_t38",
    repeats=2,
    tags=("telecom", "task:T38", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t38_trace(s, store_t38):
    meta = store_t38.seed_meta
    (
            s.user_message(_msg(store_t38))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call("run_network_diagnostics_specialist"),
                    m.tool_call("heartbeat_ping"),
                ],
                ordered=True,
                allow_extras=True,
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t38",
    repeats=2,
    tags=("telecom", "task:T38", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t38_state(s, store_t38):
    meta = store_t38.seed_meta
    (
            s.user_message(_msg(store_t38))
            .assert_that(lambda: o.assert_no_mutations(store_t38))
        )


@ek.scenario(
    agent_fixture="task_agent_t38",
    repeats=2,
    tags=("telecom", "task:T38", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t38_output(s, store_t38):
    meta = store_t38.seed_meta
    (
            s.user_message(_msg(store_t38))
            .assert_output(m.string(min_len=5))
        )
