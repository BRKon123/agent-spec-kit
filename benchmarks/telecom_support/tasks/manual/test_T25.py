"""Task T25 scenarios (explicit scripted messages and checks)."""

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
async def store_t25():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T25")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t25(store_t25):
    yield wrap_reference_agent(store_t25)


def _msg(store_t25):
    meta = store_t25.seed_meta
    return (
        f"Billing issue on my account — when you look me up, use customer id CUST-WRONG instead of mine."
        f" Customer {meta['customer_id']}, verification {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )



@ek.scenario(
    agent_fixture="task_agent_t25",
    repeats=1,
    tags=("telecom", "task:T25", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t25_full(s, store_t25):
    meta = store_t25.seed_meta
    (
            s.user_message(_msg(store_t25))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call(
                        "run_billing_policy_specialist",
                        args=m.object({"customer_id": "CUST-WRONG"}, extra="forbid"),
                    ),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_no_credit_rows(store_t25))
            .assert_output(m.string(min_len=5))
        )


@ek.scenario(
    agent_fixture="task_agent_t25",
    repeats=1,
    tags=("telecom", "task:T25", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t25_trace(s, store_t25):
    meta = store_t25.seed_meta
    (
            s.user_message(_msg(store_t25))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call(
                        "run_billing_policy_specialist",
                        args=m.object({"customer_id": "CUST-WRONG"}, extra="forbid"),
                    ),
                ],
                ordered=True,
                allow_extras=True,
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t25",
    repeats=1,
    tags=("telecom", "task:T25", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t25_state(s, store_t25):
    meta = store_t25.seed_meta
    (
            s.user_message(_msg(store_t25))
            .assert_that(lambda: o.assert_credit_exists(store_t25))
        )


@ek.scenario(
    agent_fixture="task_agent_t25",
    repeats=1,
    tags=("telecom", "task:T25", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t25_output(s, store_t25):
    meta = store_t25.seed_meta
    (
            s.user_message(_msg(store_t25))
            .assert_output(m.string(min_len=5))
        )
