"""Task T03 scenarios (explicit scripted messages and checks)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import agent_spec_kit as ek
import agent_spec_kit.match as m

from tasks.specs import oracles as o
from tasks.specs import trace_oracles as to

import shutil
import tempfile

from store.seeds import apply_seed
from store.store import TelcoStore
from agent_wrap import wrap_reference_agent


@ek.fixture
async def store_t03():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T03")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t03(store_t03):
    yield wrap_reference_agent(store_t03)


def _msg(store_t03):
    meta = store_t03.seed_meta
    return (
        f"My mobile data died near {meta['postcode']} and I don't think it's a network outage — "
        f"I haven't restarted yet and don't want a ticket, just what to try first. Account "
        f"{meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )


_T03_TRACE = [
    m.tool_call("authenticate_customer"),
    m.tool_call("check_outage"),
    m.tool_call("run_line_diagnostic"),
]

_T03_OUTPUT = m.llm_criteria(
    criteria=[
        "Offers practical troubleshooting steps such as restarting the device, toggling airplane mode, or resetting network settings",
    ],
    threshold=1,
    model="openai:gpt-5-nano",
)


@ek.scenario(
    agent_fixture="task_agent_t03",
    repeats=1,
    tags=("telecom", "task:T03", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t03_full(s, store_t03):
    (
            s.user_message(_msg(store_t03))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call("check_outage"),
                    m.tool_call("run_line_diagnostic"),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_no_tickets(store_t03))
            .assert_that(lambda: o.assert_no_credit_rows(store_t03))
            .assert_output(to.troubleshooting_without_ticket_output())
        )


@ek.scenario(
    agent_fixture="task_agent_t03",
    repeats=1,
    tags=("telecom", "task:T03", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t03_trace(s, store_t03):
    (s.user_message(_msg(store_t03)).assert_tool_calls(_T03_TRACE, ordered=True, allow_extras=True))


@ek.scenario(
    agent_fixture="task_agent_t03",
    repeats=1,
    tags=("telecom", "task:T03", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t03_state(s, store_t03):
    (
        s.user_message(_msg(store_t03))
        .assert_that(lambda: o.assert_no_tickets(store_t03))
        .assert_that(lambda: o.assert_no_credit_rows(store_t03))
    )


@ek.scenario(
    agent_fixture="task_agent_t03",
    repeats=1,
    tags=("telecom", "task:T03", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t03_output(s, store_t03):
    meta = store_t03.seed_meta
    (
            s.user_message(_msg(store_t03))
            .assert_output(to.troubleshooting_without_ticket_output())
        )
