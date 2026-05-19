"""Task T36 scenarios (explicit scripted messages and checks)."""

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
async def store_t36():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T36")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t36(store_t36):
    yield wrap_reference_agent(store_t36)


def _msg(store_t36):
    meta = store_t36.seed_meta
    return (
        f"Everyone on my street seems to be down — I'm at postcode {meta['postcode']}. "
        f"Is there an outage? I'm not asking for money back. Account {meta['customer_id']}, "
        f"verification token {meta['verification_token']}, line {meta['line_id']}."
    )



@ek.scenario(
    agent_fixture="task_agent_t36",
    repeats=1,
    tags=("telecom", "task:T36", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t36_full(s, store_t36):
    meta = store_t36.seed_meta
    (
            s.user_message(_msg(store_t36))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call("check_outage"),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_no_credit_rows(store_t36))
            .assert_that(lambda: o.assert_no_tickets(store_t36))
            .assert_output(
                m.all_of(m.contains("outage"), m.contains(meta["postcode"]))
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t36",
    repeats=1,
    tags=("telecom", "task:T36", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t36_trace(s, store_t36):
    meta = store_t36.seed_meta
    (
            s.user_message(_msg(store_t36))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call("check_outage"),
                ],
                ordered=True,
                allow_extras=True,
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t36",
    repeats=1,
    tags=("telecom", "task:T36", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t36_state(s, store_t36):
    meta = store_t36.seed_meta
    (
            s.user_message(_msg(store_t36))
            .assert_that(lambda: o.assert_no_credit_rows(store_t36))
            .assert_that(lambda: o.assert_no_tickets(store_t36))
        )


@ek.scenario(
    agent_fixture="task_agent_t36",
    repeats=1,
    tags=("telecom", "task:T36", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t36_output(s, store_t36):
    meta = store_t36.seed_meta
    (
            s.user_message(_msg(store_t36))
            .assert_output(
                m.all_of(m.contains("outage"), m.contains(meta["postcode"]))
            )
        )
