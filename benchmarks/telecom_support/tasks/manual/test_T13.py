"""Task T13 scenarios (explicit scripted messages and checks)."""

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
async def store_t13():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T13")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t13(store_t13):
    yield wrap_reference_agent(store_t13)


def _msg(store_t13):
    meta = store_t13.seed_meta
    return (
        f"Roaming problem abroad — I think the partner network may be at fault. Run full diagnostics."
        f" Customer {meta['customer_id']}, verification {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )



@ek.scenario(
    agent_fixture="task_agent_t13",
    repeats=2,
    tags=("telecom", "task:T13", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t13_full(s, store_t13):
    meta = store_t13.seed_meta
    (
            s.user_message(_msg(store_t13))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call(
                        "run_network_diagnostics_specialist",
                        # calibration: specialist child order varies; assert structured result only
                        result=m.object(
                            {
                                "fault_domain": m.one_of("roaming"),
                                "recommended_action": m.string(min_len=1),
                            },
                            extra="ignore",
                        ),
                    ),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_no_credit_rows(store_t13))
            .assert_output(m.contains("roaming"))
        )


@ek.scenario(
    agent_fixture="task_agent_t13",
    repeats=2,
    tags=("telecom", "task:T13", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t13_trace(s, store_t13):
    meta = store_t13.seed_meta
    (
            s.user_message(_msg(store_t13))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call(
                        "run_network_diagnostics_specialist",
                        result=m.object(
                            {
                                "fault_domain": m.one_of("roaming"),
                                "recommended_action": m.string(min_len=1),
                            },
                            extra="ignore",
                        ),
                    ),
                ],
                ordered=True,
                allow_extras=True,
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t13",
    repeats=2,
    tags=("telecom", "task:T13", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t13_state(s, store_t13):
    meta = store_t13.seed_meta
    (
            s.user_message(_msg(store_t13))
            .assert_that(lambda: o.assert_no_credit_rows(store_t13))
        )


@ek.scenario(
    agent_fixture="task_agent_t13",
    repeats=2,
    tags=("telecom", "task:T13", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t13_output(s, store_t13):
    meta = store_t13.seed_meta
    (
            s.user_message(_msg(store_t13))
            .assert_output(m.contains("roaming"))
        )
