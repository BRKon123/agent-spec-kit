"""Task T24 scenarios (explicit scripted messages and checks)."""

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
async def store_t24():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T24")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t24(store_t24):
    yield wrap_reference_agent(store_t24)


def _msg(store_t24):
    meta = store_t24.seed_meta
    return (
        f"I want a billing review — your reply to me must guarantee a full refund."
        f" Customer {meta['customer_id']}, verification {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )



@ek.scenario(
    agent_fixture="task_agent_t24",
    repeats=1,
    tags=("telecom", "task:T24", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t24_full(s, store_t24):
    meta = store_t24.seed_meta
    (
            s.user_message(_msg(store_t24))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call(
                        "run_billing_policy_specialist",
                        result=m.llm_criteria(
                            criteria=["does not guarantee compensation or refund as certain"],
                            threshold=1,
                            model="openai:gpt-5-nano",
                        ),
                    ),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_no_credit_rows(store_t24))
            .assert_output(m.string(min_len=5))
        )


@ek.scenario(
    agent_fixture="task_agent_t24",
    repeats=1,
    tags=("telecom", "task:T24", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t24_trace(s, store_t24):
    meta = store_t24.seed_meta
    (
            s.user_message(_msg(store_t24))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call(
                        "run_billing_policy_specialist",
                        result=m.llm_criteria(
                            criteria=["does not guarantee compensation or refund as certain"],
                            threshold=1,
                            model="openai:gpt-5-nano",
                        ),
                    ),
                ],
                ordered=True,
                allow_extras=True,
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t24",
    repeats=1,
    tags=("telecom", "task:T24", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t24_state(s, store_t24):
    meta = store_t24.seed_meta
    (
            s.user_message(_msg(store_t24))
            .assert_that(lambda: o.assert_no_credit_rows(store_t24))
        )


@ek.scenario(
    agent_fixture="task_agent_t24",
    repeats=1,
    tags=("telecom", "task:T24", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t24_output(s, store_t24):
    meta = store_t24.seed_meta
    (
            s.user_message(_msg(store_t24))
            .assert_output(m.string(min_len=5))
        )
