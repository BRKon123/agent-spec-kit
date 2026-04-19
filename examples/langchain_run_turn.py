"""Print TurnResult events from a small multi-tool LangGraph agent (requires OPENAI_API_KEY).

Run with dev dependencies (e.g. ``uv sync --group dev``), then:

    uv run python examples/langchain_run_turn.py
"""

from __future__ import annotations

import asyncio
import os

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from rich.console import Console
from rich.pretty import pprint

from agent_spec_kit import print_rich_event_trace
from agent_spec_kit.integrations.langchain_adapter import wrap_langchain_agent


@tool
def add_integers(a: int, b: int) -> int:
    """Add two integers and return the sum."""
    return a + b


@tool
def multiply_integers(a: int, b: int) -> int:
    """Multiply two integers and return the product."""
    return a * b


@tool
def secret_word() -> str:
    """Return a fixed codeword used by the demo."""
    return "plugh"


async def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        print("Set OPENAI_API_KEY to run this example.")
        raise SystemExit(1)
    console = Console()
    llm = ChatOpenAI(model="gpt-5-nano", temperature=0)
    graph = create_react_agent(llm, [add_integers, multiply_integers, secret_word])
    adapted = wrap_langchain_agent(
        graph,
        lambda msg: {"messages": [HumanMessage(content=msg)]},
        stream_mode="updates",
        version="v2",
    )
    r = await adapted.run_turn(
        "You have add_integers, multiply_integers, and secret_word. "
        "1) Call add_integers with a=10 and b=32. "
        "2) Call multiply_integers with a equal to that sum and b=2. "
        "3) Call secret_word once. "
        "4) Reply with one line: the sum, a space, the product, a space, the secret word."
    )
    console.rule("[bold]Turn summary[/bold]")
    pprint({"status": r.status, "error": r.error, "output": r.output})
    console.rule("[bold]Event trace (tree)[/bold]")
    print_rich_event_trace(console, r.events)
    console.rule("[bold]Raw events (with children)[/bold]")
    for i, ev in enumerate(r.events):
        console.print(f"[dim]— root {i} —[/dim]")
        pprint(ev)


if __name__ == "__main__":
    asyncio.run(main())
