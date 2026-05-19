"""Task T37 scenarios (explicit scripted messages and checks)."""

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
async def store_t37():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T37")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t37(store_t37):
    yield wrap_reference_agent(store_t37)


def _msg1(store_t37):
    meta = store_t37.seed_meta
    return (
        f"My line diagnostic failed. Please send me a device restart step."
        f" Customer {meta['customer_id']}, verification {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )

def _msg2(store_t37):
    meta = store_t37.seed_meta
    return (
        f"I completed the device restart on line {meta['line_id']}. Please continue and "
        f"open a support ticket with the diagnostic context."
        f" Customer {meta['customer_id']}, verification {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )



@ek.scenario(
    agent_fixture="task_agent_t37",
    repeats=1,
    tags=("telecom", "task:T37", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t37_full(s, store_t37):
    meta = store_t37.seed_meta
    (
            s.user_message(_msg1(store_t37))
        .user_message(_msg2(store_t37))
            .assert_tool_calls([
                    m.tool_call('record_user_action'),
                    m.tool_call('run_line_diagnostic'),
                    m.tool_call('create_support_ticket'),
                ], ordered=True, allow_extras=True)
            .assert_that(lambda: o.assert_ticket_exists(store_t37))
            .assert_output(m.contains("ticket"))
        )


@ek.scenario(
    agent_fixture="task_agent_t37",
    repeats=1,
    tags=("telecom", "task:T37", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t37_trace(s, store_t37):
    meta = store_t37.seed_meta
    (
            s.user_message(_msg1(store_t37))
        .user_message(_msg2(store_t37))
            .assert_tool_calls([
                    m.tool_call('record_user_action'),
                    m.tool_call('run_line_diagnostic'),
                    m.tool_call('create_support_ticket'),
                ], ordered=True, allow_extras=True)
        )


@ek.scenario(
    agent_fixture="task_agent_t37",
    repeats=1,
    tags=("telecom", "task:T37", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t37_state(s, store_t37):
    meta = store_t37.seed_meta
    (
            s.user_message(_msg1(store_t37))
        .user_message(_msg2(store_t37))
            .assert_that(lambda: o.assert_ticket_exists(store_t37))
        )


@ek.scenario(
    agent_fixture="task_agent_t37",
    repeats=1,
    tags=("telecom", "task:T37", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t37_output(s, store_t37):
    meta = store_t37.seed_meta
    (
            s.user_message(_msg1(store_t37))
        .user_message(_msg2(store_t37))
            .assert_output(m.contains("ticket"))
        )
