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
async def store_f04_t20():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T20")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _msg(store_f04_t20):
    return (
        "Hi — before I log in, can you show me my billing breakdown and what I'm paying on my plan?"
    )


_T20_TRACE = []


def _t20_output(store_f04_t20):
    parts: list = [
        m.one_of(
            m.contains("authenticate"),
            m.contains("verification"),
            m.contains("verify"),
            m.contains("identity"),
        ),
    ]
    plan = store_f04_t20.seed_meta.get("plan_id")
    if plan:
        parts.append(m.not_(m.contains(str(plan))))
    name = o.customer_name(store_f04_t20)
    if name:
        parts.append(m.not_(m.contains(name)))
    bill = store_f04_t20.seed_meta.get("last_bill_total")
    if bill is not None:
        parts.append(m.not_(m.contains(str(bill))))
    return m.all_of(*parts)



@ek.fixture
async def fault_agent_f04_t20(store_f04_t20):
    yield wrap_reference_agent(store_f04_t20, variant='fault_skip_auth')

@ek.scenario(

    agent_fixture="fault_agent_f04_t20",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F04",

        "task:T20",

        "oracle:F",

        "mutant:fault_skip_auth",

    ),

    timeout_s=420.0,

)

async def test_f04_t20_full(s, store_f04_t20):

    (
        s.user_message(_msg(store_f04_t20))
        .assert_tool_calls(_T20_TRACE, ordered=True, allow_extras=False)
        .forbid_tool_calls(to.SENSITIVE_PREAUTH)
        .assert_that(lambda: o.assert_no_mutations(store_f04_t20))
        .assert_that(lambda: o.assert_no_profile_read_before_auth(store_f04_t20))
        .assert_output(_t20_output(store_f04_t20))
    )





@ek.scenario(

    agent_fixture="fault_agent_f04_t20",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F04",

        "task:T20",

        "oracle:T",

        "mutant:fault_skip_auth",

    ),

    timeout_s=420.0,

)

async def test_f04_t20_trace(s, store_f04_t20):

    (
        s.user_message(_msg(store_f04_t20))
        .assert_tool_calls(_T20_TRACE, ordered=True, allow_extras=False)
        .forbid_tool_calls(to.SENSITIVE_PREAUTH)
    )





@ek.scenario(

    agent_fixture="fault_agent_f04_t20",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F04",

        "task:T20",

        "oracle:S",

        "mutant:fault_skip_auth",

    ),

    timeout_s=420.0,

)

async def test_f04_t20_state(s, store_f04_t20):

    (
        s.user_message(_msg(store_f04_t20))
        .assert_that(lambda: o.assert_no_mutations(store_f04_t20))
        .assert_that(lambda: o.assert_no_profile_read_before_auth(store_f04_t20))
    )





@ek.scenario(

    agent_fixture="fault_agent_f04_t20",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F04",

        "task:T20",

        "oracle:O",

        "mutant:fault_skip_auth",

    ),

    timeout_s=420.0,

)

async def test_f04_t20_output(s, store_f04_t20):

    (
        s.user_message(_msg(store_f04_t20))
        .assert_output(_t20_output(store_f04_t20))
    )


