"""Shared LangChain agent wrapper (no fixtures — safe to import from scenario modules)."""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from agent_spec_kit.integrations.langchain_adapter import wrap_langchain_agent
from agents.reference import build_graph
from store.store import TelcoStore


def wrap_reference_agent(store: TelcoStore, *, variant: str = "reference"):
    graph = build_graph(store, variant=variant)
    return wrap_langchain_agent(
        graph,
        lambda msg: {"messages": [HumanMessage(content=msg)]},
        stream_mode="updates",
        version="v2",
        subgraphs=True,
    )
