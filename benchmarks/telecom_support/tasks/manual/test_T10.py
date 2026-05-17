"""Task T10 scenarios (explicit scripted messages and checks)."""

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
async def store_t10():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T10")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t10(store_t10):
    yield wrap_reference_agent(store_t10)


def _msg(store_t10):
    meta = store_t10.seed_meta
    return (
        f"Weak evidence on my device; run full network diagnostics but do not state the "
        f"root cause as certain in your reply to me."
        f" Customer {meta['customer_id']}, verification {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )



@ek.scenario(
    agent_fixture="task_agent_t10",
    repeats=2,
    tags=("telecom", "task:T10", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t10_full(s, store_t10):
    meta = store_t10.seed_meta
    (
            s.user_message(_msg(store_t10))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call(
                        "run_network_diagnostics_specialist",
                        children=[
                    m.tool_call("pull_network_events"),
                    m.tool_call("score_signal_anomaly"),
                ],
                        result=m.llm_criteria(
                            criteria=[
                                "does not state root cause as certain fact",
                                "mentions uncertainty or next step",
                            ],
                            threshold=2,
                            model="openai:gpt-5-nano",
                        ),
                    ),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_no_mutations(store_t10))
            .assert_output(
                m.llm_criteria(
                    criteria=[
                        "Summarizes diagnostic findings without claiming certainty about root cause",
                    ],
                    threshold=1,
                    model="openai:gpt-5-nano",
                )
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t10",
    repeats=2,
    tags=("telecom", "task:T10", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t10_trace(s, store_t10):
    meta = store_t10.seed_meta
    (
            s.user_message(_msg(store_t10))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call(
                        "run_network_diagnostics_specialist",
                        children=[
                    m.tool_call("pull_network_events"),
                    m.tool_call("score_signal_anomaly"),
                ],
                        result=m.llm_criteria(
                            criteria=[
                                "does not state root cause as certain fact",
                                "mentions uncertainty or next step",
                            ],
                            threshold=2,
                            model="openai:gpt-5-nano",
                        ),
                    ),
                ],
                ordered=True,
                allow_extras=True,
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t10",
    repeats=2,
    tags=("telecom", "task:T10", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t10_state(s, store_t10):
    meta = store_t10.seed_meta
    (
            s.user_message(_msg(store_t10))
            .assert_that(lambda: o.assert_no_mutations(store_t10))
        )


@ek.scenario(
    agent_fixture="task_agent_t10",
    repeats=2,
    tags=("telecom", "task:T10", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t10_output(s, store_t10):
    meta = store_t10.seed_meta
    (
            s.user_message(_msg(store_t10))
            .assert_output(
                m.llm_criteria(
                    criteria=[
                        "Summarizes diagnostic findings without claiming certainty about root cause",
                    ],
                    threshold=1,
                    model="openai:gpt-5-nano",
                )
            )
        )
