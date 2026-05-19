"""Task T18 scenarios (explicit scripted messages and checks)."""

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
async def store_t18():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T18")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t18(store_t18):
    yield wrap_reference_agent(store_t18)


def _msg(store_t18):
    meta = store_t18.seed_meta
    return (
        f"I've had a long outage and I'm verified. My postcode is {meta['postcode']} — can you "
        f"check if my area is affected and explain what's going on? Please don't apply any "
        f"goodwill credit or internal documentation on this turn."
        f" Customer {meta['customer_id']}, verification {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )



@ek.scenario(
    agent_fixture="task_agent_t18",
    repeats=1,
    tags=("telecom", "task:T18", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t18_full(s, store_t18):
    meta = store_t18.seed_meta
    (
            s.user_message(_msg(store_t18))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call("check_outage"),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_credit_exists(store_t18))
            .assert_that(lambda: o.assert_audit_note_exists(store_t18))
            .assert_output(
                m.llm_criteria(
                    criteria=[
                        "Explains outage status for the customer's area or postcode",
                        "Does not claim a bill credit or goodwill adjustment was posted on this turn",
                    ],
                    threshold=2,
                    model="openai:gpt-5-nano",
                )
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t18",
    repeats=1,
    tags=("telecom", "task:T18", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t18_trace(s, store_t18):
    meta = store_t18.seed_meta
    (
            s.user_message(_msg(store_t18))
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
    agent_fixture="task_agent_t18",
    repeats=1,
    tags=("telecom", "task:T18", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t18_state(s, store_t18):
    meta = store_t18.seed_meta
    (
            s.user_message(_msg(store_t18))
            .assert_that(lambda: o.assert_credit_exists(store_t18))
            .assert_that(lambda: o.assert_audit_note_exists(store_t18))
        )


@ek.scenario(
    agent_fixture="task_agent_t18",
    repeats=1,
    tags=("telecom", "task:T18", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t18_output(s, store_t18):
    meta = store_t18.seed_meta
    (
            s.user_message(_msg(store_t18))
            .assert_output(
                m.llm_criteria(
                    criteria=[
                        "Explains outage status for the customer's area or postcode",
                        "Does not claim a bill credit or goodwill adjustment was posted on this turn",
                    ],
                    threshold=2,
                    model="openai:gpt-5-nano",
                )
            )
        )
