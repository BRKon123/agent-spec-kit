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

from agent_wrap import wrap_reference_agent




import shutil
import tempfile

from store.seeds import apply_seed
from store.store import TelcoStore

@ek.fixture
async def store_t09():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T09")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)

def _msg(store_t09):
    meta = store_t09.seed_meta
    return (
        f"Something's off with my connection — keeps dropping and I'm not sure why. "
        f"Can you dig into it? Account {meta['customer_id']}, verification token "
        f"{meta['verification_token']}, line {meta['line_id']}."
    )



@ek.fixture
async def fault_agent_t09(store_t09):
    yield wrap_reference_agent(store_t09, variant='fault_structured_output')

@ek.scenario(

    agent_fixture="fault_agent_t09",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F06",

        "task:T09",

        "oracle:F",

        "mutant:fault_structured_output",

    ),

    timeout_s=420.0,

)

async def test_f06_t09_full(s, store_t09):

    meta = store_t09.seed_meta
    (
            s.user_message(_msg(store_t09))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call(
                        "run_network_diagnostics_specialist",
                        children=[
                    m.tool_call("pull_network_events"),
                    m.tool_call("score_signal_anomaly"),
                ],
                        result=m.object(
                            {
                                "severity": m.one_of("high"),
                                "recommended_action": m.one_of("create_ticket"),
                                "escalation_reason": m.string(min_len=1),
                            },
                            extra="forbid",
                        ),
                    ),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_no_credit_rows(store_t09))
            .assert_output(m.string(min_len=5))
        )





@ek.scenario(

    agent_fixture="fault_agent_t09",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F06",

        "task:T09",

        "oracle:T",

        "mutant:fault_structured_output",

    ),

    timeout_s=420.0,

)

async def test_f06_t09_trace(s, store_t09):

    meta = store_t09.seed_meta
    (
            s.user_message(_msg(store_t09))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call(
                        "run_network_diagnostics_specialist",
                        children=[
                    m.tool_call("pull_network_events"),
                    m.tool_call("score_signal_anomaly"),
                ],
                        result=m.object(
                            {
                                "severity": m.one_of("high"),
                                "recommended_action": m.one_of("create_ticket"),
                                "escalation_reason": m.string(min_len=1),
                            },
                            extra="forbid",
                        ),
                    ),
                ],
                ordered=True,
                allow_extras=True,
            )
        )





@ek.scenario(

    agent_fixture="fault_agent_t09",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F06",

        "task:T09",

        "oracle:S",

        "mutant:fault_structured_output",

    ),

    timeout_s=420.0,

)

async def test_f06_t09_state(s, store_t09):

    meta = store_t09.seed_meta
    (
            s.user_message(_msg(store_t09))
            .assert_that(lambda: o.assert_no_credit_rows(store_t09))
        )





@ek.scenario(

    agent_fixture="fault_agent_t09",

    repeats=1,

    tags=(

        "telecom",

        "fault-detection",

        "fault:F06",

        "task:T09",

        "oracle:O",

        "mutant:fault_structured_output",

    ),

    timeout_s=420.0,

)

async def test_f06_t09_output(s, store_t09):

    meta = store_t09.seed_meta
    (
            s.user_message(_msg(store_t09))
            .assert_output(m.string(min_len=5))
        )


