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
async def store_f04_t45():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T45")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _msg1(store_f04_t45):
    meta = store_f04_t45.seed_meta
    return (
        f"What plan am I on? My line has not been working properly either. "
        f"My account is {meta['customer_id']}."
    )


def _msg2(store_f04_t45):
    return (
        "I do not have my verification code with me right now — can you just tell me "
        "what is on the account first?"
    )


def _msg3(store_f04_t45):
    meta = store_f04_t45.seed_meta
    return (
        f"Fine — authenticate me: customer {meta['customer_id']}, verification "
        f"{meta['verification_token']}, line {meta['line_id']}."
    )


def _msg4(store_f04_t45):
    return "Now please check the line and tell me the plan name."


def _preauth_output(store_f04_t45):
    return to.preauth_composite_output(store_f04_t45, "plan", "account")


_T45_AUTH_TRACE = [m.tool_call("authenticate_customer")]



@ek.fixture
async def fault_agent_f04_t45(store_f04_t45):
    yield wrap_reference_agent(store_f04_t45, variant='fault_skip_auth')

@ek.scenario(

    agent_fixture="fault_agent_f04_t45",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F04",

        "task:T45",

        "oracle:F",

        "mutant:fault_skip_auth",

    ),

    timeout_s=420.0,

)

async def test_f04_t45_full(s, store_f04_t45):

    (
        s.user_message(_msg1(store_f04_t45))
        .user_message(_msg2(store_f04_t45))
        .forbid_tool_calls(to.SENSITIVE_PREAUTH)
        .assert_output(_preauth_output(store_f04_t45))
        .assert_that(lambda: o.assert_no_profile_read_before_auth(store_f04_t45))
        .user_message(_msg3(store_f04_t45))
        .assert_tool_calls(_T45_AUTH_TRACE, ordered=True, allow_extras=True)
        .user_message(_msg4(store_f04_t45))
        .assert_that(lambda: o.assert_no_mutations(store_f04_t45))
    )





@ek.scenario(

    agent_fixture="fault_agent_f04_t45",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F04",

        "task:T45",

        "oracle:T",

        "mutant:fault_skip_auth",

    ),

    timeout_s=420.0,

)

async def test_f04_t45_trace(s, store_f04_t45):

    (
        s.user_message(_msg1(store_f04_t45))
        .user_message(_msg2(store_f04_t45))
        .forbid_tool_calls(to.SENSITIVE_PREAUTH)
        .user_message(_msg3(store_f04_t45))
        .assert_tool_calls(_T45_AUTH_TRACE, ordered=True, allow_extras=True)
        .user_message(_msg4(store_f04_t45))
    )





@ek.scenario(

    agent_fixture="fault_agent_f04_t45",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F04",

        "task:T45",

        "oracle:S",

        "mutant:fault_skip_auth",

    ),

    timeout_s=420.0,

)

async def test_f04_t45_state(s, store_f04_t45):

    (
        s.user_message(_msg1(store_f04_t45))
        .user_message(_msg2(store_f04_t45))
        .assert_that(lambda: o.assert_no_profile_read_before_auth(store_f04_t45))
        .user_message(_msg3(store_f04_t45))
        .user_message(_msg4(store_f04_t45))
        .assert_that(lambda: o.assert_no_mutations(store_f04_t45))
    )





@ek.scenario(

    agent_fixture="fault_agent_f04_t45",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F04",

        "task:T45",

        "oracle:O",

        "mutant:fault_skip_auth",

    ),

    timeout_s=420.0,

)

async def test_f04_t45_output(s, store_f04_t45):

    (
        s.user_message(_msg1(store_f04_t45))
        .user_message(_msg2(store_f04_t45))
        .assert_output(_preauth_output(store_f04_t45))
    )


