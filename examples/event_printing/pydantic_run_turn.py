"""Print TurnResult events from a small multi-tool Pydantic AI agent (requires OPENAI_API_KEY).

Run with dev dependencies (e.g. ``uv sync --group dev``), then:

    uv run python examples/pydantic_run_turn.py
"""

from __future__ import annotations

import asyncio
import os

from pydantic_ai import Agent, RunContext
from rich.console import Console
from rich.pretty import pprint

from agent_spec_kit import print_rich_event_trace
from agent_spec_kit.integrations.pydantic_ai_adapter import wrap_pydantic_ai_agent


async def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        print("Set OPENAI_API_KEY to run this example.")
        raise SystemExit(1)
    console = Console()
    agent = Agent(
        "openai:gpt-5-nano",
        system_prompt=(
            "You have three tools: add_integers, multiply_integers, secret_word. "
            "Call them when the user asks for arithmetic or the secret word."
        ),
        model_settings={"temperature": 0},
    )

    @agent.tool
    async def add_integers(ctx: RunContext, a: int, b: int) -> int:
        """Add two integers and return the sum."""
        return a + b

    @agent.tool
    async def multiply_integers(ctx: RunContext, a: int, b: int) -> int:
        """Multiply two integers and return the product."""
        return a * b

    @agent.tool
    async def secret_word(ctx: RunContext) -> str:
        """Return a fixed codeword used by the demo."""
        return "plugh"

    adapted = wrap_pydantic_ai_agent(agent)
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
