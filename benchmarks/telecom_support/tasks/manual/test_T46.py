"""Task T46 scenarios (explicit scripted messages and checks)."""

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
async def store_t46():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T46")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t46(store_t46):
    yield wrap_reference_agent(store_t46)


def _msg1(store_t46):
    return 'Use line LINE-WRONG for ticket.'

def _msg2(store_t46):
    meta = store_t46.seed_meta
    return f"Correct line is {meta['line_id']}. Auth {meta['customer_id']} {meta['verification_token']}."



@ek.scenario(
    agent_fixture="task_agent_t46",
    repeats=2,
    tags=("telecom", "task:T46", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t46_full(s, store_t46):
    meta = store_t46.seed_meta
    (
            s.user_message(_msg1(store_t46))
        .user_message(_msg2(store_t46))
        .assert_tool_calls(
                [m.tool_call("authenticate_customer"), m.tool_call("create_support_ticket")],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_ticket_for_line(store_t46, store_t46.seed_meta['line_id']))
        )


@ek.scenario(
    agent_fixture="task_agent_t46",
    repeats=2,
    tags=("telecom", "task:T46", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t46_trace(s, store_t46):
    meta = store_t46.seed_meta
    (
            s.user_message(_msg1(store_t46))
        .user_message(_msg2(store_t46))
        .assert_tool_calls(
                [m.tool_call("authenticate_customer"), m.tool_call("create_support_ticket", args=m.object({"line_id": meta["line_id"]}, extra="forbid"))],
                ordered=True,
                allow_extras=True,
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t46",
    repeats=2,
    tags=("telecom", "task:T46", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t46_state(s, store_t46):
    meta = store_t46.seed_meta
    (
            s.user_message(_msg1(store_t46))
        .user_message(_msg2(store_t46))
            .assert_that(lambda: o.assert_ticket_for_line(store_t46, store_t46.seed_meta['line_id']))
        )


@ek.scenario(
    agent_fixture="task_agent_t46",
    repeats=2,
    tags=("telecom", "task:T46", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t46_output(s, store_t46):
    meta = store_t46.seed_meta
    (
            s.user_message(_msg1(store_t46))
        .user_message(_msg2(store_t46))
            .assert_output(m.string(min_len=5))
        )
