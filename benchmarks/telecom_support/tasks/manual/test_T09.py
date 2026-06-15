"""Task T09 scenarios (explicit scripted messages and checks)."""

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
async def store_t09():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T09")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t09(store_t09):
    yield wrap_reference_agent(store_t09)


def _msg(store_t09):
    meta = store_t09.seed_meta
    return (
        f"Something's off with my connection — keeps dropping and I'm not sure why. "
        f"Can you dig into it? Account {meta['customer_id']}, verification token "
        f"{meta['verification_token']}, line {meta['line_id']}."
    )


_T09_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call(
        "run_network_diagnostics_specialist",
        children=[
            m.tool_call("pull_network_events"),
            m.tool_call("score_signal_anomaly"),
        ],
        result=m.object(
            {
                "severity": m.one_of("high"),
                "recommended_action": m.one_of("create_ticket"),
                "escalation_reason": m.string(min_len=1),
            },
            extra="forbid",
        ),
    ),
]

_T09_OUTPUT = m.llm_criteria(
    criteria=[
        "Summarizes network diagnostic findings for the customer",
    ],
    threshold=1,
    model="openai:gpt-5-nano",
)


@ek.scenario(
    agent_fixture="task_agent_t09",
    repeats=1,
    tags=("telecom", "task:T09", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t09_full(s, store_t09):
    (
        s.user_message(_msg(store_t09))
        .assert_tool_calls(_T09_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_no_credit_rows(store_t09))
        .assert_output(_T09_OUTPUT)
    )


@ek.scenario(
    agent_fixture="task_agent_t09",
    repeats=1,
    tags=("telecom", "task:T09", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t09_trace(s, store_t09):
    (s.user_message(_msg(store_t09)).assert_tool_calls(_T09_TRACE, ordered=True, allow_extras=True))


@ek.scenario(
    agent_fixture="task_agent_t09",
    repeats=1,
    tags=("telecom", "task:T09", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t09_state(s, store_t09):
    (s.user_message(_msg(store_t09)).assert_that(lambda: o.assert_no_credit_rows(store_t09)))


@ek.scenario(
    agent_fixture="task_agent_t09",
    repeats=1,
    tags=("telecom", "task:T09", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t09_output(s, store_t09):
    (s.user_message(_msg(store_t09)).assert_output(_T09_OUTPUT))
