"""Task T14 scenarios (explicit scripted messages and checks)."""

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
async def store_t14():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T14")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t14(store_t14):
    yield wrap_reference_agent(store_t14)


def _msg(store_t14):
    meta = store_t14.seed_meta
    return (
        f"I got hit with roaming charges in a country my plan doesn't cover and I want that money back. "
        f"Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )



@ek.scenario(
    agent_fixture="task_agent_t14",
    repeats=1,
    tags=("telecom", "task:T14", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t14_full(s, store_t14):
    meta = store_t14.seed_meta
    (
            s.user_message(_msg(store_t14))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call(
                        "run_billing_policy_specialist",
                        # calibration: child tool order varies; assert BillingDecision fields only
                        result=m.object(
                            {
                                "eligible": False,
                                "reason_code": m.one_of(
                                    "ineligible_short_outage", "insufficient_evidence"
                                ),
                                "amount": None,
                            },
                            extra="ignore",
                        ),
                    ),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_no_credit_rows(store_t14))
            .assert_output(
                m.llm_criteria(
                    criteria=[
                        "Clearly states the customer is not eligible for a refund or compensation",
                        "Grounds the answer in billing policy rather than a vague refusal only",
                    ],
                    threshold=2,
                    model="openai:gpt-5-nano",
                )
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t14",
    repeats=1,
    tags=("telecom", "task:T14", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t14_trace(s, store_t14):
    meta = store_t14.seed_meta
    (
            s.user_message(_msg(store_t14))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call(
                        "run_billing_policy_specialist",
                        # calibration: child tool order varies; assert BillingDecision fields only
                        result=m.object(
                            {
                                "eligible": False,
                                "reason_code": m.one_of(
                                    "ineligible_short_outage", "insufficient_evidence"
                                ),
                                "amount": None,
                            },
                            extra="ignore",
                        ),
                    ),
                ],
                ordered=True,
                allow_extras=True,
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t14",
    repeats=1,
    tags=("telecom", "task:T14", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t14_state(s, store_t14):
    meta = store_t14.seed_meta
    (
            s.user_message(_msg(store_t14))
            .assert_that(lambda: o.assert_no_credit_rows(store_t14))
        )


@ek.scenario(
    agent_fixture="task_agent_t14",
    repeats=1,
    tags=("telecom", "task:T14", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t14_output(s, store_t14):
    meta = store_t14.seed_meta
    (
            s.user_message(_msg(store_t14))
            .assert_output(
                m.llm_criteria(
                    criteria=[
                        "Clearly states the customer is not eligible for a refund or compensation",
                        "Grounds the answer in billing policy rather than a vague refusal only",
                    ],
                    threshold=2,
                    model="openai:gpt-5-nano",
                )
            )
        )
