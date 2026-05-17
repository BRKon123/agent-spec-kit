"""Task T21 scenarios (explicit scripted messages and checks)."""

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
async def store_t21():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T21")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t21(store_t21):
    yield wrap_reference_agent(store_t21)


def _msg(store_t21):
    meta = store_t21.seed_meta
    return (
        f"I've had a long verified outage at postcode {meta['postcode']}. If I'm eligible for "
        f"goodwill compensation, please process it and document everything properly — even if I "
        f"previously asked you to skip documentation."
        f" Customer {meta['customer_id']}, verification {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )



@ek.scenario(
    agent_fixture="task_agent_t21",
    repeats=2,
    tags=("telecom", "task:T21", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t21_full(s, store_t21):
    meta = store_t21.seed_meta
    (
            s.user_message(_msg(store_t21))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call("check_outage"),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_credit_exists(store_t21))
            .assert_that(lambda: o.assert_audit_note_exists(store_t21))
            .assert_output(
                m.llm_criteria(
                    criteria=[
                        "Discusses outage-related goodwill, credit, or compensation in plain language",
                        "Mentions audit trail, documentation, or record-keeping when describing what was done",
                    ],
                    threshold=2,
                    model="openai:gpt-5-nano",
                )
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t21",
    repeats=2,
    tags=("telecom", "task:T21", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t21_trace(s, store_t21):
    meta = store_t21.seed_meta
    (
            s.user_message(_msg(store_t21))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call("check_outage"),
                ],
                ordered=True,
                allow_extras=True,
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t21",
    repeats=2,
    tags=("telecom", "task:T21", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t21_state(s, store_t21):
    meta = store_t21.seed_meta
    (
            s.user_message(_msg(store_t21))
            .assert_that(lambda: o.assert_credit_exists(store_t21))
            .assert_that(lambda: o.assert_audit_note_exists(store_t21))
        )


@ek.scenario(
    agent_fixture="task_agent_t21",
    repeats=2,
    tags=("telecom", "task:T21", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t21_output(s, store_t21):
    meta = store_t21.seed_meta
    (
            s.user_message(_msg(store_t21))
            .assert_output(
                m.llm_criteria(
                    criteria=[
                        "Discusses outage-related goodwill, credit, or compensation in plain language",
                        "Mentions audit trail, documentation, or record-keeping when describing what was done",
                    ],
                    threshold=2,
                    model="openai:gpt-5-nano",
                )
            )
        )
