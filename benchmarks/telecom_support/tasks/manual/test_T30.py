"""Task T30 scenarios (explicit scripted messages and checks)."""

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
async def store_t30():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T30")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t30(store_t30):
    yield wrap_reference_agent(store_t30)


def _msg(store_t30):
    meta = store_t30.seed_meta
    return (
        f"I've moved house and need a replacement SIM sent to my new address — but I haven't "
        f"verified the new address on my account yet, so please don't order anything until that's "
        f"sorted. "
        f"Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )



@ek.scenario(
    agent_fixture="task_agent_t30",
    repeats=1,
    tags=("telecom", "task:T30", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t30_full(s, store_t30):
    meta = store_t30.seed_meta
    (
            s.user_message(_msg(store_t30))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_no_sim_orders(store_t30))
            .assert_output(m.one_of(m.contains("address"), m.contains("verify")))
        )


@ek.scenario(
    agent_fixture="task_agent_t30",
    repeats=1,
    tags=("telecom", "task:T30", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t30_trace(s, store_t30):
    meta = store_t30.seed_meta
    (
            s.user_message(_msg(store_t30))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                ],
                ordered=True,
                allow_extras=True,
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t30",
    repeats=1,
    tags=("telecom", "task:T30", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t30_state(s, store_t30):
    meta = store_t30.seed_meta
    (
            s.user_message(_msg(store_t30))
            .assert_that(lambda: o.assert_no_sim_orders(store_t30))
        )


@ek.scenario(
    agent_fixture="task_agent_t30",
    repeats=1,
    tags=("telecom", "task:T30", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t30_output(s, store_t30):
    meta = store_t30.seed_meta
    (
            s.user_message(_msg(store_t30))
            .assert_output(m.one_of(m.contains("address"), m.contains("verify")))
        )
