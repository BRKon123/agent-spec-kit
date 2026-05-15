"""Build LangGraph ReAct agents for the telco benchmark."""

from __future__ import annotations

import os

from langgraph.prebuilt import create_react_agent

from agents.prompts import fault_system_prompt, reference_system_prompt
from store.store import TelcoStore
from store.tools import make_tools


def require_api_key() -> None:
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        raise RuntimeError(
            "TelcoSupportBench-Lite requires OPENAI_API_KEY "
            "(install dependency-groups dev and export the key)."
        )


def build_graph(store: TelcoStore, *, variant: str = "reference") -> object:
    require_api_key()
    from langchain_openai import ChatOpenAI

    tools = make_tools(store, variant=variant)
    prompt = (
        reference_system_prompt()
        if variant == "reference"
        else fault_system_prompt(variant)
    )
    llm = ChatOpenAI(model="gpt-5-nano", temperature=0)
    return create_react_agent(llm, tools, prompt=prompt)
