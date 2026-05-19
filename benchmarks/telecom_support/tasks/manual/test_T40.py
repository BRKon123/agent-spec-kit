"""Task T40 scenarios (explicit scripted messages and checks)."""

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
async def store_t40():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T40")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t40(store_t40):
    yield wrap_reference_agent(store_t40)


def _msg(store_t40):
    meta = store_t40.seed_meta
    return (
        f"Intermittent signal drops — review recent network events before scoring how unusual the signal is."
        f" Customer {meta['customer_id']}, verification {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )



@ek.scenario(
    agent_fixture="task_agent_t40",
    repeats=1,
    tags=("telecom", "task:T40", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t40_full(s, store_t40):
    meta = store_t40.seed_meta
    (
            s.user_message(_msg(store_t40))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call(
                        "run_network_diagnostics_specialist",
                        children=[
                            m.tool_call("pull_network_events"),
                            m.tool_call("score_signal_anomaly"),
                        ],
                    ),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_no_mutations(store_t40))
            .assert_output(m.string(min_len=5))
        )


@ek.scenario(
    agent_fixture="task_agent_t40",
    repeats=1,
    tags=("telecom", "task:T40", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t40_trace(s, store_t40):
    meta = store_t40.seed_meta
    (
            s.user_message(_msg(store_t40))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call(
                        "run_network_diagnostics_specialist",
                        children=[
                            m.tool_call("pull_network_events"),
                            m.tool_call("score_signal_anomaly"),
                        ],
                    ),
                ],
                ordered=True,
                allow_extras=True,
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t40",
    repeats=1,
    tags=("telecom", "task:T40", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t40_state(s, store_t40):
    meta = store_t40.seed_meta
    (
            s.user_message(_msg(store_t40))
            .assert_that(lambda: o.assert_no_mutations(store_t40))
        )


@ek.scenario(
    agent_fixture="task_agent_t40",
    repeats=1,
    tags=("telecom", "task:T40", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t40_output(s, store_t40):
    meta = store_t40.seed_meta
    (
            s.user_message(_msg(store_t40))
            .assert_output(m.string(min_len=5))
        )
