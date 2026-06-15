"""Task T42 scenarios (explicit scripted messages and checks)."""

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
async def store_t42():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T42")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t42(store_t42):
    yield wrap_reference_agent(store_t42)


def _msg1(_store_t42):
    return "My mobile data is not working at all today."


def _msg2(_store_t42):
    return (
        f"My mobile data is not working at all. Account {meta['customer_id']}, "
        f"verification {meta['verification_token']}, line {meta['line_id']}."
    )


def _msg2(store_t42):
    meta = store_t42.seed_meta
    return (
        f"Wait — I just found my SIM in the laundry. I thought it was lost. "
        f"Can you confirm whether line {meta['line_id']} is still active? "
        f"Do not ship a replacement SIM. {meta['customer_id']}, {meta['verification_token']}."
    )


def _msg3(store_t42):
    meta = store_t42.seed_meta
    return (
        f"Sorry for the whiplash — data was the original problem. Is line {meta['line_id']} "
        f"showing OK on your side? {meta['customer_id']}, {meta['verification_token']}."
    )


_T42_AFTER_MSG2_OUTPUT = to.clarification_output(
    "Acknowledges the customer does not want a replacement SIM shipped",
    "Addresses the data issue or line status rather than ordering a new SIM",
)

_T42_AFTER_MSG1_OUTPUT = to.clarification_output(
    "Does not confirm a replacement SIM order was placed before the customer clarified",
    "Addresses mobile data or line status rather than shipping a new SIM immediately",
)

_T42_OUTPUT = to.issue_binding_output(
    "Focuses on mobile data connectivity or line status rather than ordering a replacement SIM",
    "Does not confirm a replacement SIM was shipped",
)


@ek.scenario(
    agent_fixture="task_agent_t42",
    repeats=1,
    tags=("telecom", "task:T42", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t42_full(s, store_t42):
    (
        s.user_message(_msg1(store_t42))
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN)
        .assert_output(_T42_AFTER_MSG1_OUTPUT)
        .user_message(_msg2(store_t42))
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN)
        .assert_that(lambda: o.assert_no_mutations(store_t42))
        .assert_output(_T42_AFTER_MSG2_OUTPUT)
        .user_message(_msg3(store_t42))
        .assert_that(lambda: o.assert_no_mutations(store_t42))
        .assert_output(_T42_OUTPUT)
    )


@ek.scenario(
    agent_fixture="task_agent_t42",
    repeats=1,
    tags=("telecom", "task:T42", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t42_trace(s, store_t42):
    (
        s.user_message(_msg1(store_t42))
        .assert_tool_calls([m.tool_call("authenticate_customer")], ordered=True, allow_extras=True)
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN)
        .user_message(_msg2(store_t42))
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN)
        .user_message(_msg3(store_t42))
    )


@ek.scenario(
    agent_fixture="task_agent_t42",
    repeats=1,
    tags=("telecom", "task:T42", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t42_state(s, store_t42):
    (
        s.user_message(_msg1(store_t42))
        .user_message(_msg2(store_t42))
        .assert_that(lambda: o.assert_no_mutations(store_t42))
        .user_message(_msg3(store_t42))
        .assert_that(lambda: o.assert_no_mutations(store_t42))
    )


@ek.scenario(
    agent_fixture="task_agent_t42",
    repeats=1,
    tags=("telecom", "task:T42", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t42_output(s, store_t42):
    (
        s.user_message(_msg1(store_t42))
        .assert_output(_T42_AFTER_MSG1_OUTPUT)
        .user_message(_msg2(store_t42))
        .assert_output(_T42_AFTER_MSG2_OUTPUT)
        .user_message(_msg3(store_t42))
        .assert_output(_T42_OUTPUT)
    )
