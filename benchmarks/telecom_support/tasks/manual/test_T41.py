"""Task T41 scenarios (explicit scripted messages and checks)."""

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
async def store_t41():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T41")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t41(store_t41):
    yield wrap_reference_agent(store_t41)


def _msg(store_t41):
    meta = store_t41.seed_meta
    return (
        f"My mobile data is down and I see a duplicate charge on my bill. Please check "
        f"connectivity, diagnose my line, and review the billing all in one go — do not "
        f"apply any credit yet."
        f" Customer {meta['customer_id']}, verification {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )



@ek.scenario(
    agent_fixture="task_agent_t41",
    repeats=2,
    tags=("telecom", "task:T41", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t41_full(s, store_t41):
    meta = store_t41.seed_meta
    (
            s.user_message(_msg(store_t41))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call("check_outage"),
                    m.tool_call("run_line_diagnostic"),
                    m.tool_call("run_billing_policy_specialist"),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_no_credit_rows(store_t41))
            .assert_that(lambda: o.assert_no_tickets(store_t41))
            .assert_output(
                m.llm_criteria(
                    criteria=[
                        "Addresses both mobile data or connectivity and the duplicate billing concern",
                        "Does not claim a bill credit was applied on this turn",
                    ],
                    threshold=2,
                    model="openai:gpt-5-nano",
                )
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t41",
    repeats=2,
    tags=("telecom", "task:T41", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t41_trace(s, store_t41):
    meta = store_t41.seed_meta
    (
            s.user_message(_msg(store_t41))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call("check_outage"),
                    m.tool_call("run_line_diagnostic"),
                    m.tool_call("run_billing_policy_specialist"),
                ],
                ordered=True,
                allow_extras=True,
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t41",
    repeats=2,
    tags=("telecom", "task:T41", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t41_state(s, store_t41):
    meta = store_t41.seed_meta
    (
            s.user_message(_msg(store_t41))
            .assert_that(lambda: o.assert_no_credit_rows(store_t41))
            .assert_that(lambda: o.assert_no_tickets(store_t41))
        )


@ek.scenario(
    agent_fixture="task_agent_t41",
    repeats=2,
    tags=("telecom", "task:T41", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t41_output(s, store_t41):
    meta = store_t41.seed_meta
    (
            s.user_message(_msg(store_t41))
            .assert_output(
                m.llm_criteria(
                    criteria=[
                        "Addresses both mobile data or connectivity and the duplicate billing concern",
                        "Does not claim a bill credit was applied on this turn",
                    ],
                    threshold=2,
                    model="openai:gpt-5-nano",
                )
            )
        )
