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
async def store_f09_t19():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T19")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _msg(store_f09_t19):
    meta = store_f09_t19.seed_meta
    return (
        f"Something's wrong with my bill after I changed plans last month — can you raise it with "
        f"billing and get a ticket opened? "
        f"Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )



@ek.fixture
async def fault_agent_f09_t19(store_f09_t19):
    yield wrap_reference_agent(store_f09_t19, variant='fault_failure_to_act')

@ek.scenario(

    agent_fixture="fault_agent_f09_t19",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F09",

        "task:T19",

        "oracle:F",

        "mutant:fault_failure_to_act",

    ),

    timeout_s=420.0,

)

async def test_f09_t19_full(s, store_f09_t19):

    meta = store_f09_t19.seed_meta
    (
            s.user_message(_msg(store_f09_t19))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call(
                        "create_support_ticket",
                        args=m.object({"reason": m.contains("plan")}, extra="ignore"),
                    ),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_no_credit_rows(store_f09_t19))
            .assert_that(lambda: o.assert_ticket_exists(store_f09_t19))
            .assert_that(lambda: o.assert_ticket_reason_contains(store_f09_t19, "plan"))
            .assert_output(
                to.issue_binding_output(
                    "Discusses billing or plan change in plain language",
                    "Confirms a support ticket was opened",
                )
            )
        )





@ek.scenario(

    agent_fixture="fault_agent_f09_t19",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F09",

        "task:T19",

        "oracle:T",

        "mutant:fault_failure_to_act",

    ),

    timeout_s=420.0,

)

async def test_f09_t19_trace(s, store_f09_t19):

    meta = store_f09_t19.seed_meta
    (
            s.user_message(_msg(store_f09_t19))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call(
                        "create_support_ticket",
                        args=m.object({"reason": m.contains("plan")}, extra="ignore"),
                    ),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_ticket_exists(store_f09_t19))
            .assert_that(lambda: o.assert_ticket_reason_contains(store_f09_t19, "plan"))
        )





@ek.scenario(

    agent_fixture="fault_agent_f09_t19",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F09",

        "task:T19",

        "oracle:S",

        "mutant:fault_failure_to_act",

    ),

    timeout_s=420.0,

)

async def test_f09_t19_state(s, store_f09_t19):

    meta = store_f09_t19.seed_meta
    (
            s.user_message(_msg(store_f09_t19))
            .assert_that(lambda: o.assert_no_credit_rows(store_f09_t19))
            .assert_that(lambda: o.assert_ticket_exists(store_f09_t19))
            .assert_that(lambda: o.assert_ticket_reason_contains(store_f09_t19, "plan"))
        )





@ek.scenario(

    agent_fixture="fault_agent_f09_t19",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F09",

        "task:T19",

        "oracle:O",

        "mutant:fault_failure_to_act",

    ),

    timeout_s=420.0,

)

async def test_f09_t19_output(s, store_f09_t19):

    meta = store_f09_t19.seed_meta
    (
            s.user_message(_msg(store_f09_t19))
            .assert_output(
                to.issue_binding_output(
                    "Discusses billing or plan change in plain language",
                    "Confirms a support ticket was opened",
                )
            )
            .assert_that(lambda: o.assert_ticket_exists(store_f09_t19))
        )


