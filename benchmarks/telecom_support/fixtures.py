"""TelcoSupportBench-Lite fixtures (discovered by agent-spec-kit run)."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

_BENCH_ROOT = Path(__file__).resolve().parent
if str(_BENCH_ROOT) not in sys.path:
    sys.path.insert(0, str(_BENCH_ROOT))

import agent_spec_kit as ek
from langchain_core.messages import HumanMessage

from agent_spec_kit.integrations.langchain_adapter import wrap_langchain_agent

from agents.faults.registry import FAULT_VARIANTS
from agents.reference import build_graph
from store.seeds import apply_seed
from store.store import TelcoStore

_TASK_CASES = (
    ek.case("task_pilot_auth", id="task_pilot_auth"),
    ek.case("task_pilot_outage", id="task_pilot_outage"),
    ek.case("task_pilot_credit", id="task_pilot_credit"),
)

_FAULT_CASES = tuple(ek.case(v, id=v) for v in FAULT_VARIANTS)


def _wrap_agent(store: TelcoStore, variant: str):
    graph = build_graph(store, variant=variant)
    return wrap_langchain_agent(
        graph,
        lambda msg: {"messages": [HumanMessage(content=msg)]},
        stream_mode="updates",
        version="v2",
    )


@ek.fixture
@ek.parametrize("task_id", _TASK_CASES)
async def store(task_id: str):
    """Isolated SQLite DB per scenario job; seeded from ``seeds/{task_id}.json``."""
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, task_id)
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def adapted_agent(store: TelcoStore):
    """Reference agent (policy in prompt; permissive tools)."""
    yield _wrap_agent(store, "reference")


@ek.fixture
@ek.parametrize("agent_variant", _FAULT_CASES)
async def fault_agent(store: TelcoStore, agent_variant: str):
    """Fault-seeded agent variants for failure-detection runs."""
    yield _wrap_agent(store, agent_variant)


@ek.fixture
async def fault_unsupported_credit_agent(store: TelcoStore):
    """Single fault variant for focused detection scenarios."""
    yield _wrap_agent(store, "fault_unsupported_credit")
