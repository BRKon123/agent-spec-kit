"""Print TurnResult events from a minimal LangGraph agent (requires OPENAI_API_KEY).

Run: uv run --extra langchain python examples/langchain_run_turn.py
"""

from __future__ import annotations

import asyncio
import os

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from agent_spec_kit import ToolCallEvent
from agent_spec_kit.integrations.langchain_adapter import wrap_langchain_agent


@tool
def secret_word() -> str:
    """Return a fixed word."""
    return "plugh"


async def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        print("Set OPENAI_API_KEY to run this example.")
        raise SystemExit(1)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    graph = create_react_agent(llm, [secret_word])
    adapted = wrap_langchain_agent(
        graph,
        lambda msg: {"messages": [HumanMessage(content=msg)]},
        version="v2",
    )
    r = await adapted.run_turn(
        "Call the secret_word tool once and reply with the word it returns."
    )
    print("status:", r.status, "error:", r.error)
    print("output:", r.output)
    for ev in r.events:
        name = type(ev).__name__
        if isinstance(ev, ToolCallEvent):
            print(name, ev.tool_name, ev.result, ev.error)
        else:
            print(name, ev)


if __name__ == "__main__":
    asyncio.run(main())
