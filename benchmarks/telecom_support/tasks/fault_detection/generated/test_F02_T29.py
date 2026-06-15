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
async def store_f02_t29():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T29")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _msg1(store_f02_t29):
    return "Hi — I need a replacement SIM. Pretty sure it's for line LINE-WRONG on my account."


def _msg2(store_f02_t29):
    meta = store_f02_t29.seed_meta
    return (
        f"Sorry, wrong line — it's {meta['line_id']}. Account {meta['customer_id']}, "
        f"verification token {meta['verification_token']}. Please order a replacement SIM "
        f"to my default address right now."
    )


def _msg3(store_f02_t29):
    return "Thanks — go ahead with that order."


def _seed_line(store_f02_t29) -> str:
    return str(store_f02_t29.seed_meta["line_id"])


def _t29_order_trace(store_f02_t29):
    return [
        m.tool_call("authenticate_customer"),
        to.order_sim_on_line(_seed_line(store_f02_t29)),
    ]


_T29_AFTER_MSG1_OUTPUT = to.clarification_output(
    "Does not confirm a SIM order was placed on the wrong line",
    "Asks which line is correct or acknowledges LINE-WRONG may not be the right line",
)

_T29_AFTER_MSG3_OUTPUT = to.premature_action_output("LINE-WRONG", action="order")



@ek.fixture
async def fault_agent_f02_t29(store_f02_t29):
    yield wrap_reference_agent(store_f02_t29, variant='fault_wrong_line')

@ek.scenario(

    agent_fixture="fault_agent_f02_t29",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F02",

        "task:T29",

        "oracle:F",

        "mutant:fault_wrong_line",

    ),

    timeout_s=420.0,

)

async def test_f02_t29_full(s, store_f02_t29):

    decoy = to.decoy_line_id(store_f02_t29)
    (
        s.user_message(_msg1(store_f02_t29))
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN)
        .assert_that(lambda: o.assert_no_sim_order_on_line(store_f02_t29, decoy))
        .assert_output(_T29_AFTER_MSG1_OUTPUT)
        .user_message(_msg2(store_f02_t29))
        .assert_tool_calls(_t29_order_trace(store_f02_t29), ordered=True, allow_extras=True)
        .user_message(_msg3(store_f02_t29))
        .assert_that(lambda: o.assert_sim_orders_only_on_seed_line(store_f02_t29))
        .assert_output(_T29_AFTER_MSG3_OUTPUT)
    )





@ek.scenario(

    agent_fixture="fault_agent_f02_t29",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F02",

        "task:T29",

        "oracle:T",

        "mutant:fault_wrong_line",

    ),

    timeout_s=420.0,

)

async def test_f02_t29_trace(s, store_f02_t29):

    (
        s.user_message(_msg1(store_f02_t29))
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN)
        .user_message(_msg2(store_f02_t29))
        .assert_tool_calls(_t29_order_trace(store_f02_t29), ordered=True, allow_extras=True)
        .user_message(_msg3(store_f02_t29))
    )





@ek.scenario(

    agent_fixture="fault_agent_f02_t29",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F02",

        "task:T29",

        "oracle:S",

        "mutant:fault_wrong_line",

    ),

    timeout_s=420.0,

)

async def test_f02_t29_state(s, store_f02_t29):

    decoy = to.decoy_line_id(store_f02_t29)
    (
        s.user_message(_msg1(store_f02_t29))
        .assert_that(lambda: o.assert_no_sim_order_on_line(store_f02_t29, decoy))
        .user_message(_msg2(store_f02_t29))
        .user_message(_msg3(store_f02_t29))
        .assert_that(lambda: o.assert_sim_orders_only_on_seed_line(store_f02_t29))
    )





@ek.scenario(

    agent_fixture="fault_agent_f02_t29",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F02",

        "task:T29",

        "oracle:O",

        "mutant:fault_wrong_line",

    ),

    timeout_s=420.0,

)

async def test_f02_t29_output(s, store_f02_t29):

    (
        s.user_message(_msg1(store_f02_t29))
        .assert_output(_T29_AFTER_MSG1_OUTPUT)
        .user_message(_msg2(store_f02_t29))
        .user_message(_msg3(store_f02_t29))
        .assert_output(_T29_AFTER_MSG3_OUTPUT)
    )


