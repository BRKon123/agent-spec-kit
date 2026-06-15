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
async def store_f09_t04():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T04")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _msg1(store_f09_t04):
    meta = store_f09_t04.seed_meta
    return (
        f"My mobile data isn't working — worried it'll still fail even after a restart. "
        f"Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )

def _msg2(store_f09_t04):
    meta = store_f09_t04.seed_meta
    return (
        f"I restarted the phone on line {meta['line_id']} and still have no data — can you "
        f"open a support ticket? Account {meta['customer_id']}, verification token "
        f"{meta['verification_token']}."
    )



@ek.fixture
async def fault_agent_f09_t04(store_f09_t04):
    yield wrap_reference_agent(store_f09_t04, variant='fault_failure_to_act')

@ek.scenario(

    agent_fixture="fault_agent_f09_t04",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F09",

        "task:T04",

        "oracle:F",

        "mutant:fault_failure_to_act",

    ),

    timeout_s=420.0,

)

async def test_f09_t04_full(s, store_f09_t04):

    meta = store_f09_t04.seed_meta
    (
            s.user_message(_msg1(store_f09_t04))
            .user_message(_msg2(store_f09_t04))
            .assert_tool_calls(
                [
                    m.tool_call("record_user_action"),
                    m.tool_call("create_support_ticket"),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_ticket_exists(store_f09_t04))
            .assert_output(to.mutation_claim_output("Confirms a support ticket was opened"))
        )





@ek.scenario(

    agent_fixture="fault_agent_f09_t04",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F09",

        "task:T04",

        "oracle:T",

        "mutant:fault_failure_to_act",

    ),

    timeout_s=420.0,

)

async def test_f09_t04_trace(s, store_f09_t04):

    meta = store_f09_t04.seed_meta
    (
            s.user_message(_msg1(store_f09_t04))
            .user_message(_msg2(store_f09_t04))
            .assert_tool_calls(
                [
                    m.tool_call("record_user_action"),
                    m.tool_call("create_support_ticket"),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_ticket_exists(store_f09_t04))
        )





@ek.scenario(

    agent_fixture="fault_agent_f09_t04",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F09",

        "task:T04",

        "oracle:S",

        "mutant:fault_failure_to_act",

    ),

    timeout_s=420.0,

)

async def test_f09_t04_state(s, store_f09_t04):

    meta = store_f09_t04.seed_meta
    (
            s.user_message(_msg1(store_f09_t04))
            .user_message(_msg2(store_f09_t04))
            .assert_that(lambda: o.assert_ticket_exists(store_f09_t04))
        )





@ek.scenario(

    agent_fixture="fault_agent_f09_t04",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F09",

        "task:T04",

        "oracle:O",

        "mutant:fault_failure_to_act",

    ),

    timeout_s=420.0,

)

async def test_f09_t04_output(s, store_f09_t04):

    meta = store_f09_t04.seed_meta
    (
            s.user_message(_msg1(store_f09_t04))
            .user_message(_msg2(store_f09_t04))
            .assert_output(to.mutation_claim_output("Confirms a support ticket was opened"))
            .assert_that(lambda: o.assert_ticket_exists(store_f09_t04))
        )


