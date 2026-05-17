"""Task T26 scenarios (explicit scripted messages and checks)."""

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
async def store_t26():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T26")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t26(store_t26):
    yield wrap_reference_agent(store_t26)


def _msg(store_t26):
    meta = store_t26.seed_meta
    return (
        f"I lost my physical SIM card. Please ship a physical replacement to my default "
        f"address for line {meta['line_id']}."
        f" Customer {meta['customer_id']}, verification {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )



@ek.scenario(
    agent_fixture="task_agent_t26",
    repeats=2,
    tags=("telecom", "task:T26", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t26_full(s, store_t26):
    meta = store_t26.seed_meta
    (
            s.user_message(_msg(store_t26))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call("order_replacement_sim", args=m.object({"sim_type": m.one_of("physical")}, extra="ignore")),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_sim_order_exists(store_t26))
            .assert_that(lambda: o.assert_audit_note_exists(store_t26))
            .assert_output(m.one_of(m.contains("replacement"), m.contains("SIM")))
        )


@ek.scenario(
    agent_fixture="task_agent_t26",
    repeats=2,
    tags=("telecom", "task:T26", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t26_trace(s, store_t26):
    meta = store_t26.seed_meta
    (
            s.user_message(_msg(store_t26))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call("order_replacement_sim"),
                ],
                ordered=True,
                allow_extras=True,
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t26",
    repeats=2,
    tags=("telecom", "task:T26", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t26_state(s, store_t26):
    meta = store_t26.seed_meta
    (
            s.user_message(_msg(store_t26))
            .assert_that(lambda: o.assert_sim_order_exists(store_t26))
            .assert_that(lambda: o.assert_audit_note_exists(store_t26))
        )


@ek.scenario(
    agent_fixture="task_agent_t26",
    repeats=2,
    tags=("telecom", "task:T26", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t26_output(s, store_t26):
    meta = store_t26.seed_meta
    (
            s.user_message(_msg(store_t26))
            .assert_output(m.one_of(m.contains("replacement"), m.contains("SIM")))
        )
