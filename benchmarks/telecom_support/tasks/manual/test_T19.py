"""Task T19 scenarios (explicit scripted messages and checks)."""

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
async def store_t19():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T19")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t19(store_t19):
    yield wrap_reference_agent(store_t19)


def _msg(store_t19):
    meta = store_t19.seed_meta
    return (
        f"Something's wrong with my bill after I changed plans last month — can you raise it with "
        f"billing and get a ticket opened? "
        f"Account {meta['customer_id']}, verification token {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )



@ek.scenario(
    agent_fixture="task_agent_t19",
    repeats=1,
    tags=("telecom", "task:T19", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t19_full(s, store_t19):
    meta = store_t19.seed_meta
    (
            s.user_message(_msg(store_t19))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call(
                        "create_support_ticket",
                        args=m.object({"reason": m.contains("plan")}, extra="ignore"),
                    ),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_no_credit_rows(store_t19))
            .assert_that(lambda: o.assert_ticket_exists(store_t19))
            .assert_output(m.contains("ticket"))
        )


@ek.scenario(
    agent_fixture="task_agent_t19",
    repeats=1,
    tags=("telecom", "task:T19", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t19_trace(s, store_t19):
    meta = store_t19.seed_meta
    (
            s.user_message(_msg(store_t19))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call("create_support_ticket"),
                ],
                ordered=True,
                allow_extras=True,
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t19",
    repeats=1,
    tags=("telecom", "task:T19", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t19_state(s, store_t19):
    meta = store_t19.seed_meta
    (
            s.user_message(_msg(store_t19))
            .assert_that(lambda: o.assert_no_credit_rows(store_t19))
            .assert_that(lambda: o.assert_ticket_exists(store_t19))
        )


@ek.scenario(
    agent_fixture="task_agent_t19",
    repeats=1,
    tags=("telecom", "task:T19", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t19_output(s, store_t19):
    meta = store_t19.seed_meta
    (
            s.user_message(_msg(store_t19))
            .assert_output(m.contains("ticket"))
        )
