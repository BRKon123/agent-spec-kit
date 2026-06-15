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
async def store_f02_t43():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T43")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _stale_line(store_f02_t43):
    return o.stale_line_id(store_f02_t43)


def _seed_line(store_f02_t43):
    return str(store_f02_t43.seed_meta["line_id"])


def _msg1(store_f02_t43):
    stale = _stale_line(store_f02_t43)
    return f"Please open a support ticket on {stale} — my SIM will not connect on that line."


def _msg2(store_f02_t43):
    return "Sorry, that is the wrong line — I meant our main phone instead."


def _msg3(store_f02_t43):
    meta = store_f02_t43.seed_meta
    seed = _seed_line(store_f02_t43)
    return (
        f"Yes use {seed} for the ticket. Account {meta['customer_id']}, verification "
        f"{meta['verification_token']}."
    )


_T43_AUTH_TRACE = [m.tool_call("authenticate_customer")]

_T43_AFTER_MSG2_OUTPUT = to.clarification_output(
    "Acknowledges the customer corrected which line needs the ticket",
    "Does not confirm a ticket was opened on the wrong line before correction",
)

_T43_OUTPUT = to.issue_binding_output(
    "Confirms a support ticket on the customer's main line for SIM or connectivity",
    "Does not describe the issue only as a billing or plan dispute",
)



@ek.fixture
async def fault_agent_f02_t43(store_f02_t43):
    yield wrap_reference_agent(store_f02_t43, variant='fault_stale_belief')

@ek.scenario(

    agent_fixture="fault_agent_f02_t43",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F02",

        "task:T43",

        "oracle:F",

        "mutant:fault_stale_belief",

    ),

    timeout_s=420.0,

)

async def test_f02_t43_full(s, store_f02_t43):

    stale = _stale_line(store_f02_t43)
    (
        s.user_message(_msg1(store_f02_t43))
        .forbid_tool_calls(to.PREMATURE_TICKET)
        .user_message(_msg2(store_f02_t43))
        .forbid_tool_calls(to.PREMATURE_TICKET)
        .assert_output(_T43_AFTER_MSG2_OUTPUT)
        .assert_that(lambda: o.assert_no_ticket_on_line(store_f02_t43, stale))
        .user_message(_msg3(store_f02_t43))
        .assert_tool_calls(_T43_AUTH_TRACE, ordered=True, allow_extras=True)
        .assert_that(lambda: o.assert_no_ticket_on_line(store_f02_t43, stale))
        .assert_that(
            lambda: o.assert_latest_ticket_reason_excludes(
                store_f02_t43, "billing", "invoice", "plan dispute"
            )
        )
        .assert_output(_T43_OUTPUT)
    )





@ek.scenario(

    agent_fixture="fault_agent_f02_t43",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F02",

        "task:T43",

        "oracle:T",

        "mutant:fault_stale_belief",

    ),

    timeout_s=420.0,

)

async def test_f02_t43_trace(s, store_f02_t43):

    (
        s.user_message(_msg1(store_f02_t43))
        .forbid_tool_calls(to.PREMATURE_TICKET)
        .user_message(_msg2(store_f02_t43))
        .forbid_tool_calls(to.PREMATURE_TICKET)
        .user_message(_msg3(store_f02_t43))
        .assert_tool_calls(_T43_AUTH_TRACE, ordered=True, allow_extras=True)
    )





@ek.scenario(

    agent_fixture="fault_agent_f02_t43",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F02",

        "task:T43",

        "oracle:S",

        "mutant:fault_stale_belief",

    ),

    timeout_s=420.0,

)

async def test_f02_t43_state(s, store_f02_t43):

    stale = _stale_line(store_f02_t43)
    (
        s.user_message(_msg1(store_f02_t43))
        .user_message(_msg2(store_f02_t43))
        .assert_that(lambda: o.assert_no_ticket_on_line(store_f02_t43, stale))
        .user_message(_msg3(store_f02_t43))
        .assert_that(lambda: o.assert_no_ticket_on_line(store_f02_t43, stale))
        .assert_that(
            lambda: o.assert_latest_ticket_reason_excludes(
                store_f02_t43, "billing", "invoice", "plan dispute"
            )
        )
    )





@ek.scenario(

    agent_fixture="fault_agent_f02_t43",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F02",

        "task:T43",

        "oracle:O",

        "mutant:fault_stale_belief",

    ),

    timeout_s=420.0,

)

async def test_f02_t43_output(s, store_f02_t43):

    (
        s.user_message(_msg1(store_f02_t43))
        .user_message(_msg2(store_f02_t43))
        .assert_output(_T43_AFTER_MSG2_OUTPUT)
        .user_message(_msg3(store_f02_t43))
        .assert_output(_T43_OUTPUT)
    )


