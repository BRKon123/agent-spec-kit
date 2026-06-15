"""Task T16 scenarios (explicit scripted messages and checks)."""

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
async def store_t16():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T16")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t16(store_t16):
    yield wrap_reference_agent(store_t16)


def _msg(store_t16):
    meta = store_t16.seed_meta
    return (
        f"There's what looks like a duplicate charge on my latest bill — am I owed a refund? "
        f"Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )


_T16_OUTPUT = m.llm_criteria(
    criteria=[
        "Addresses the duplicate charge or billing dispute",
        "Mentions a refund, bill credit, or that the customer is owed money",
    ],
    threshold=2,
    model="openai:gpt-5-nano",
)

_T16_OUTPUT_FULL = m.llm_criteria(
    criteria=[
        "Addresses the duplicate charge or billing dispute",
        "Does not state that a credit was posted or an audit note was recorded on this turn",
    ],
    threshold=2,
    model="openai:gpt-5-nano",
)


@ek.scenario(
    agent_fixture="task_agent_t16",
    repeats=1,
    tags=("telecom", "task:T16", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t16_full(s, store_t16):
    (
            s.user_message(_msg(store_t16))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call("run_billing_policy_specialist"),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_credit_exists(store_t16))
            .assert_that(lambda: o.assert_audit_note_exists(store_t16))
            .assert_output(_T16_OUTPUT_FULL)
        )


@ek.scenario(
    agent_fixture="task_agent_t16",
    repeats=1,
    tags=("telecom", "task:T16", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t16_trace(s, store_t16):
    (s.user_message(_msg(store_t16)).assert_tool_calls(_T16_TRACE, ordered=True, allow_extras=True))


@ek.scenario(
    agent_fixture="task_agent_t16",
    repeats=1,
    tags=("telecom", "task:T16", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t16_state(s, store_t16):
    (
        s.user_message(_msg(store_t16))
        .assert_that(lambda: o.assert_credit_exists(store_t16))
        .assert_that(lambda: o.assert_audit_note_exists(store_t16))
    )


@ek.scenario(
    agent_fixture="task_agent_t16",
    repeats=1,
    tags=("telecom", "task:T16", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t16_output(s, store_t16):
    meta = store_t16.seed_meta
    (
            s.user_message(_msg(store_t16))
            .assert_output(_T16_OUTPUT)
        )
