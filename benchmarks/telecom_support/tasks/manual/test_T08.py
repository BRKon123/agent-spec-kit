"""Task T08 scenarios (explicit scripted messages and checks)."""

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
async def store_t08():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T08")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t08(store_t08):
    yield wrap_reference_agent(store_t08)


def _msg(store_t08):
    meta = store_t08.seed_meta
    return (
        f"Open a support ticket for my data issue with reason 'general problem' only."
        f" Customer {meta['customer_id']}, verification {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )



@ek.scenario(
    agent_fixture="task_agent_t08",
    repeats=2,
    tags=("telecom", "task:T08", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t08_full(s, store_t08):
    meta = store_t08.seed_meta
    (
            s.user_message(_msg(store_t08))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call(
                        "create_support_ticket",
                        args=m.object(
                            {"reason": m.contains("diagnostic")},
                            extra="forbid",
                        ),
                    ),
                ],
                ordered=True,
                allow_extras=True,
            )
            .assert_that(lambda: o.assert_ticket_exists(store_t08))
            .assert_output(m.contains("ticket"))
        )


@ek.scenario(
    agent_fixture="task_agent_t08",
    repeats=2,
    tags=("telecom", "task:T08", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t08_trace(s, store_t08):
    meta = store_t08.seed_meta
    (
            s.user_message(_msg(store_t08))
            .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                    m.tool_call(
                        "create_support_ticket",
                        args=m.object(
                            {"reason": m.contains("diagnostic")},
                            extra="forbid",
                        ),
                    ),
                ],
                ordered=True,
                allow_extras=True,
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t08",
    repeats=2,
    tags=("telecom", "task:T08", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t08_state(s, store_t08):
    meta = store_t08.seed_meta
    (
            s.user_message(_msg(store_t08))
            .assert_that(lambda: o.assert_ticket_exists(store_t08))
        )


@ek.scenario(
    agent_fixture="task_agent_t08",
    repeats=2,
    tags=("telecom", "task:T08", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t08_output(s, store_t08):
    meta = store_t08.seed_meta
    (
            s.user_message(_msg(store_t08))
            .assert_output(m.contains("ticket"))
        )
