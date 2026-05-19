"""Shared LangChain agent wrapper (no fixtures — safe to import from scenario modules)."""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from agent_spec_kit.integrations.langchain_adapter import wrap_langchain_agent
from agents.reference import build_graph
from store.store import TelcoStore

# Embedded reference faults for catalog-Fail tasks (used when calibration steering is off).
_TASK_FAULT_VARIANTS: dict[str, str] = {
    "T21": "fault_audit_omission",
    "T26": "fault_audit_omission",
    "T46": "fault_stale_belief",
    "T47": "fault_unsupported_credit",
    "T50": "fault_auth_bypass",
}


def wrap_reference_agent(store: TelcoStore, *, variant: str = "reference"):
    if variant == "reference":
        tid = str(store.seed_meta.get("task_id", ""))
        variant = _TASK_FAULT_VARIANTS.get(tid, "reference")
    graph = build_graph(store, variant=variant)
    return wrap_langchain_agent(
        graph,
        lambda msg: {"messages": [HumanMessage(content=msg)]},
        stream_mode="updates",
        version="v2",
        subgraphs=True,
    )
