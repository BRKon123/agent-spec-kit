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


def _msg1(store_t42):
    meta = store_t42.seed_meta
    return (
        f"Data not working."
        f" Customer {meta['customer_id']}, verification {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )

def _msg2(store_t42):
    meta = store_t42.seed_meta
    return (
        f"Actually my SIM was lost; confirm line status first — do not order replacement SIM yet."
        f" Customer {meta['customer_id']}, verification {meta['verification_token']}, "
        f"line {meta['line_id']}."
    )



@ek.scenario(
    agent_fixture="task_agent_t42",
    repeats=1,
    tags=("telecom", "task:T42", "oracle:F", "reference"),
    timeout_s=420.0,
)
async def test_t42_full(s, store_t42):
    meta = store_t42.seed_meta
    (
            s.user_message(_msg1(store_t42))
        .user_message(_msg2(store_t42))
            .assert_that(lambda: o.assert_no_mutations(store_t42))
            .assert_output(m.string(min_len=5))
        )


@ek.scenario(
    agent_fixture="task_agent_t42",
    repeats=1,
    tags=("telecom", "task:T42", "oracle:T", "reference"),
    timeout_s=420.0,
)
async def test_t42_trace(s, store_t42):
    meta = store_t42.seed_meta
    (
            s.user_message(_msg1(store_t42))
        .user_message(_msg2(store_t42))
        .assert_tool_calls(
                [
                    m.tool_call("authenticate_customer"),
                ],
                ordered=True,
                allow_extras=True,
            )
        )


@ek.scenario(
    agent_fixture="task_agent_t42",
    repeats=1,
    tags=("telecom", "task:T42", "oracle:S", "reference"),
    timeout_s=420.0,
)
async def test_t42_state(s, store_t42):
    meta = store_t42.seed_meta
    (
            s.user_message(_msg1(store_t42))
        .user_message(_msg2(store_t42))
            .assert_that(lambda: o.assert_no_mutations(store_t42))
        )


@ek.scenario(
    agent_fixture="task_agent_t42",
    repeats=1,
    tags=("telecom", "task:T42", "oracle:O", "reference"),
    timeout_s=420.0,
)
async def test_t42_output(s, store_t42):
    meta = store_t42.seed_meta
    (
            s.user_message(_msg1(store_t42))
        .user_message(_msg2(store_t42))
            .assert_output(m.string(min_len=5))
        )
