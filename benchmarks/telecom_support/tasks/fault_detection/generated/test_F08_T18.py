"""Generated fault-detection scenarios — do not edit by hand.

Regenerate: uv run python benchmarks/telecom_support/scripts/bootstrap_fault_detection.py
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import agent_spec_kit as ek
import agent_spec_kit.match as m
from tasks.specs import oracles as o
from tasks.specs import trace_oracles as to
from agent_wrap import wrap_reference_agent



import shutil
import tempfile

from store.seeds import apply_seed
from store.store import TelcoStore

@ek.fixture
async def store_f08_t18():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T18")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _msg(store_f08_t18):
    meta = store_f08_t18.seed_meta
    return (
        f"We've had a long outage at home — postcode {meta['postcode']}. Is there still an outage "
        f"in our area and what's going on? "
        f"Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )



@ek.fixture
async def fault_agent_f08_t18(store_f08_t18):
    yield wrap_reference_agent(store_f08_t18, variant='fault_audit_omission')

@ek.scenario(

    agent_fixture="fault_agent_f08_t18",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F08",

        "task:T18",

        "oracle:F",

        "mutant:fault_audit_omission",

    ),

    timeout_s=420.0,

)

async def test_f08_t18_full(s, store_f08_t18):

    meta = store_f08_t18.seed_meta
    (
            s.user_message(_msg(store_f08_t18))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call("check_outage"),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_credit_exists(store_f08_t18))
            .assert_that(lambda: o.assert_audit_note_exists(store_f08_t18))
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

    agent_fixture="fault_agent_f08_t18",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F08",

        "task:T18",

        "oracle:T",

        "mutant:fault_audit_omission",

    ),

    timeout_s=420.0,

)

async def test_f08_t18_trace(s, store_f08_t18):

    meta = store_f08_t18.seed_meta
    (
            s.user_message(_msg(store_f08_t18))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call("check_outage"),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_audit_note_exists(store_f08_t18))
        )





@ek.scenario(

    agent_fixture="fault_agent_f08_t18",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F08",

        "task:T18",

        "oracle:S",

        "mutant:fault_audit_omission",

    ),

    timeout_s=420.0,

)

async def test_f08_t18_state(s, store_f08_t18):

    meta = store_f08_t18.seed_meta
    (
            s.user_message(_msg(store_f08_t18))
            .assert_that(lambda: o.assert_credit_exists(store_f08_t18))
            .assert_that(lambda: o.assert_audit_note_exists(store_f08_t18))
        )





@ek.scenario(

    agent_fixture="fault_agent_f08_t18",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F08",

        "task:T18",

        "oracle:O",

        "mutant:fault_audit_omission",

    ),

    timeout_s=420.0,

)

async def test_f08_t18_output(s, store_f08_t18):

    meta = store_f08_t18.seed_meta
    (
            s.user_message(_msg(store_f08_t18))
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


