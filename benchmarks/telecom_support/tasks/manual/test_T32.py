"""Task T32 scenarios (explicit scripted messages and checks)."""

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
async def store_t32():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T32")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t32(store_t32):
    yield wrap_reference_agent(store_t32)


def _msg1(store_t32):
    return "Hi — my SIM stopped working on line LINE-WRONG. I need a replacement sent out."


def _msg2(store_t32):
    meta = store_t32.seed_meta
    lid2 = meta.get("line_id_2", meta["line_id"])
    return (
        f"Sorry, wrong line — it's actually {lid2}, not LINE-WRONG. "
        f"Account {meta['customer_id']}, verification token {meta['verification_token']}."
    )


def _msg3(store_t32):
    meta = store_t32.seed_meta
    lid2 = meta.get("line_id_2", meta["line_id"])
    return f"Yes please — ship the replacement SIM to my default address for {lid2}."


def _trace_after_correction(store_t32):
    meta = store_t32.seed_meta
    lid2 = meta.get("line_id_2", meta["line_id"])
    return [
        m.tool_call("authenticate_customer"),
        m.tool_call(
            "order_replacement_sim",
            args=m.object({"line_id": lid2}, extra="forbid"),
        ),
    ]


@ek.scenario(
    agent_fixture="task_agent_t32",
    repeats=1,
    tags=("telecom", "task:T32", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t32_full(s, store_t32):
    (
        s.user_message(_msg1(store_t32))
        .user_message(_msg2(store_t32))
        .user_message(_msg3(store_t32))
        .assert_tool_calls(_trace_after_correction(store_t32), ordered=True, allow_extras=True)
        .assert_that(
            lambda: o.assert_sim_order_for_line(
                store_t32, store_t32.seed_meta.get("line_id_2", store_t32.seed_meta["line_id"])
            )
        )
    )


@ek.scenario(
    agent_fixture="task_agent_t32",
    repeats=1,
    tags=("telecom", "task:T32", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t32_trace(s, store_t32):
    (
        s.user_message(_msg1(store_t32))
        .user_message(_msg2(store_t32))
        .user_message(_msg3(store_t32))
        .assert_tool_calls(_trace_after_correction(store_t32), ordered=True, allow_extras=True)
    )


@ek.scenario(
    agent_fixture="task_agent_t32",
    repeats=1,
    tags=("telecom", "task:T32", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t32_state(s, store_t32):
    (
        s.user_message(_msg1(store_t32))
        .user_message(_msg2(store_t32))
        .user_message(_msg3(store_t32))
        .assert_that(
            lambda: o.assert_sim_order_for_line(
                store_t32, store_t32.seed_meta.get("line_id_2", store_t32.seed_meta["line_id"])
            )
        )
    )


@ek.scenario(
    agent_fixture="task_agent_t32",
    repeats=1,
    tags=("telecom", "task:T32", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t32_output(s, store_t32):
    (
        s.user_message(_msg1(store_t32))
        .user_message(_msg2(store_t32))
        .user_message(_msg3(store_t32))
        .assert_output(m.string(min_len=5))
    )
