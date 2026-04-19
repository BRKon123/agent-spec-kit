"""Live LangChain + OpenAI integration (skipped without API key)."""

from __future__ import annotations

import asyncio
import os

import pytest
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from agent_spec_kit import ToolCallEvent
from agent_spec_kit.integrations.langchain_adapter import wrap_langchain_agent

pytestmark = pytest.mark.integration


@tool
def secret_word() -> str:
    """Return the secret test word."""
    return "plugh"


def _has_openai() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


@pytest.mark.skipif(not _has_openai(), reason="OPENAI_API_KEY not set")
def test_live_react_agent_tool_and_output() -> None:
    async def body() -> None:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        graph = create_react_agent(llm, [secret_word])
        adapted = wrap_langchain_agent(
            graph,
            lambda msg: {"messages": [HumanMessage(content=msg)]},
            stream_mode="updates",
            version="v2",
        )
        r = await adapted.run_turn(
            "You must call the secret_word tool exactly once, then reply with only the word it returns."
        )
        assert r.status == "ok", r.error
        assert r.output is not None
        tool_names = [e.tool_name for e in r.events if isinstance(e, ToolCallEvent)]
        assert "secret_word" in tool_names
        assert "plugh" in str(r.output).lower() or any(
            "plugh" in str(e.result).lower()
            for e in r.events
            if isinstance(e, ToolCallEvent) and e.result is not None
        )

    asyncio.run(body())
