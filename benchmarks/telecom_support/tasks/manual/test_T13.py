"""Task T13 scenarios (explicit scripted messages and checks)."""

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
async def store_t13():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T13")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t13(store_t13):
    yield wrap_reference_agent(store_t13)


def _msg1(_store_t13):
    return (
        "Roaming's been awful since I landed — calls drop and data barely works. "
        "Feels like the local partner network rather than my phone. Can you dig into what's wrong?"
    )


def _msg2(store_t13):
    meta = store_t13.seed_meta
    return (
        f"Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']} — please run diagnostics on the roaming issue."
    )


_T13_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call(
        "run_network_diagnostics_specialist",
        result=m.object(
            {
                "fault_domain": m.one_of("roaming"),
                "recommended_action": m.string(min_len=1),
            },
            extra="ignore",
        ),
    ),
]

_T13_OUTPUT = m.one_of(
    m.llm_criteria(
        criteria=[
            "Discusses roaming or partner-network issues in plain language",
            "Does not guarantee a specific root cause without evidence",
        ],
        threshold=2,
        model="openai:gpt-5-nano",
    ),
    m.contains("roaming"),
)


@ek.scenario(
    agent_fixture="task_agent_t13",
    repeats=1,
    tags=("telecom", "task:T13", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t13_full(s, store_t13):
    (
        s.user_message(_msg1(store_t13))
        .user_message(_msg2(store_t13))
        .assert_tool_calls(_T13_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_no_credit_rows(store_t13))
        .assert_output(_T13_OUTPUT)
    )


@ek.scenario(
    agent_fixture="task_agent_t13",
    repeats=1,
    tags=("telecom", "task:T13", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t13_trace(s, store_t13):
    (
        s.user_message(_msg1(store_t13))
        .user_message(_msg2(store_t13))
        .assert_tool_calls(_T13_TRACE, ordered=True, allow_extras=True)
    )


@ek.scenario(
    agent_fixture="task_agent_t13",
    repeats=1,
    tags=("telecom", "task:T13", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t13_state(s, store_t13):
    (
        s.user_message(_msg1(store_t13))
        .user_message(_msg2(store_t13))
        .assert_that(lambda: o.assert_no_credit_rows(store_t13))
    )


@ek.scenario(
    agent_fixture="task_agent_t13",
    repeats=1,
    tags=("telecom", "task:T13", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t13_output(s, store_t13):
    (
        s.user_message(_msg1(store_t13))
        .user_message(_msg2(store_t13))
        .assert_output(_T13_OUTPUT)
    )
