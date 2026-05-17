"""Task T01 scenarios (explicit scripted messages and checks)."""

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
async def store_t01():
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T01")
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def task_agent_t01(store_t01):
    yield wrap_reference_agent(store_t01)


def _msg(store_t01):
    meta = store_t01.seed_meta
    return (
        f"My mobile data is not working. Investigation only — please do not open tickets or "
        f"apply credits. Check the status of line {meta['line_id']} and explain whether mobile "
        f"data is enabled."
        f" Customer {meta['customer_id']}, verification {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )


@ek.scenario(
    agent_fixture="task_agent_t01",
    repeats=2,
    tags=("telecom", "task:T01", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t01_full(s, store_t01):
    (
    s.user_message(_msg(store_t01))
    .assert_tool_calls(
            [
                m.tool_call("authenticate_customer"),
                m.tool_call(
                    "get_line_status",
                    args=m.object({"line_id": m.string()}),
                ),
            ],
            ordered=True,
            allow_extras=True,
        )
    .assert_that(lambda: o.assert_no_mutations(store_t01))
    .assert_output(m.one_of(m.contains("data"), m.contains("LINE-0001")))
    )

@ek.scenario(
    agent_fixture="task_agent_t01",
    repeats=2,
    tags=("telecom", "task:T01", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t01_trace(s, store_t01):
    (
    s.user_message(_msg(store_t01))
    .assert_tool_calls(
            [
                m.tool_call("authenticate_customer"),
                m.tool_call(
                    "get_line_status",
                    args=m.object({"line_id": m.string()}),
                ),
            ],
            ordered=True,
            allow_extras=True,
        )
    )

@ek.scenario(
    agent_fixture="task_agent_t01",
    repeats=2,
    tags=("telecom", "task:T01", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t01_state(s, store_t01):
    (
    s.user_message(_msg(store_t01))
    .assert_that(lambda: o.assert_no_mutations(store_t01))
    )

@ek.scenario(
    agent_fixture="task_agent_t01",
    repeats=2,
    tags=("telecom", "task:T01", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t01_output(s, store_t01):
    (
    s.user_message(_msg(store_t01))
    .assert_output(m.one_of(m.contains("data"), m.contains("LINE-0001")))
    )
