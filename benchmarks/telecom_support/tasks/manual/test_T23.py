"""Task T23 scenarios (explicit scripted messages and checks)."""

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
async def store_t23():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T23")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t23(store_t23):
    yield wrap_reference_agent(store_t23)


def _msg(store_t23):
    meta = store_t23.seed_meta
    return (
        f"I was charged twice for the same thing. Please assess whether I'm eligible for a "
        f"refund and tell me the amount if I am — but don't post any credit to my account yet."
        f" Customer {meta['customer_id']}, verification {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )



@ek.scenario(
    agent_fixture="task_agent_t23",
    repeats=1,
    tags=("telecom", "task:T23", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t23_full(s, store_t23):
    meta = store_t23.seed_meta
    (
            s.user_message(_msg(store_t23))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call('run_billing_policy_specialist', result=m.object({'eligible': True, 'amount': m.number(min=0.01)}, extra='forbid')),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_no_credit_rows(store_t23))
            .assert_output(
                m.llm_criteria(
                    criteria=[
                        "States whether the customer is eligible for a duplicate-charge refund",
                        "Includes a specific refund amount when stating eligibility",
                    ],
                    threshold=2,
                    model="openai:gpt-5-nano",
                )
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t23",
    repeats=1,
    tags=("telecom", "task:T23", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t23_trace(s, store_t23):
    meta = store_t23.seed_meta
    (
            s.user_message(_msg(store_t23))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call('run_billing_policy_specialist', result=m.object({'eligible': True, 'amount': m.number(min=0.01)}, extra='forbid')),
                ],
                ordered=True,
                allow_extras=True,
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t23",
    repeats=1,
    tags=("telecom", "task:T23", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t23_state(s, store_t23):
    meta = store_t23.seed_meta
    (
            s.user_message(_msg(store_t23))
            .assert_that(lambda: o.assert_no_credit_rows(store_t23))
        )


@ek.scenario(
    agent_fixture="task_agent_t23",
    repeats=1,
    tags=("telecom", "task:T23", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t23_output(s, store_t23):
    meta = store_t23.seed_meta
    (
            s.user_message(_msg(store_t23))
            .assert_output(
                m.llm_criteria(
                    criteria=[
                        "States whether the customer is eligible for a duplicate-charge refund",
                        "Includes a specific refund amount when stating eligibility",
                    ],
                    threshold=2,
                    model="openai:gpt-5-nano",
                )
            )
        )
