"""TelcoSupportBench fixtures (discovered by agent-spec-kit run)."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

_BENCH_ROOT = Path(__file__).resolve().parent
if str(_BENCH_ROOT) not in sys.path:
    sys.path.insert(0, str(_BENCH_ROOT))

import agent_spec_kit as ek

from agent_wrap import wrap_reference_agent
from agents.faults.registry import FAULT_VARIANTS
from agents.reference import build_graph
from store.seeds import apply_seed
from store.store import TelcoStore

_PILOT_CASES = (
    ek.case("task_pilot_auth", id="task_pilot_auth"),
    ek.case("task_pilot_outage", id="task_pilot_outage"),
    ek.case("task_pilot_credit", id="task_pilot_credit"),
)

_FAULT_CASES = tuple(ek.case(v, id=v) for v in FAULT_VARIANTS)


def _wrap_agent(store: TelcoStore, variant: str):
  if variant == "reference":
    return wrap_reference_agent(store)
  graph = build_graph(store, variant=variant)
  from langchain_core.messages import HumanMessage
  from agent_spec_kit.integrations.langchain_adapter import wrap_langchain_agent
  return wrap_langchain_agent(
    graph,
    lambda msg: {"messages": [HumanMessage(content=msg)]},
    stream_mode="updates",
    version="v2",
    subgraphs=True,
  )


@ek.fixture
@ek.parametrize("task_id", _PILOT_CASES)
async def pilot_store(task_id: str):
    """Pilot seeds (``test_pilot_tasks.py``). Task files define their own ``store``."""
    base = Path(tempfile.mkdtemp(prefix="telco_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, task_id)
        yield telco
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def adapted_agent(pilot_store: TelcoStore):
    """Reference agent for pilot scenarios."""
    yield wrap_reference_agent(pilot_store)


@ek.fixture
@ek.parametrize("agent_variant", _FAULT_CASES)
async def fault_agent(pilot_store: TelcoStore, agent_variant: str):
    """Fault-seeded agent variants for failure-detection runs."""
    yield _wrap_agent(pilot_store, agent_variant)


@ek.fixture
async def fault_unsupported_credit_agent(pilot_store: TelcoStore):
    """Single fault variant for focused detection scenarios."""
    yield _wrap_agent(pilot_store, "fault_unsupported_credit")
