"""
Nested Pydantic AI agents: one root ``AgentTurnEvent`` with optional nested tools.

Adds **parallel outer tools** (`run_analyst` + `sidecar_ping`) so the outer agent may emit
sibling ``ToolCallEvent`` nodes in one round. Inner ``add_inner`` may nest under
``run_analyst`` when the stream exposes it.
"""

from __future__ import annotations

import asyncio
import os

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from rich.console import Console
from rich.pretty import pprint

from agent_spec_kit import print_rich_event_trace
from agent_spec_kit.integrations.pydantic_ai_adapter import wrap_pydantic_ai_agent


class ArithmeticReport(BaseModel):
    sum_value: int = Field(description="Sum of 10 and 32")
    product: int = Field(description="sum_value times 2")
    inner_tool_call: bool = Field(description="Whether the inner tool was called")


async def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        print("Set OPENAI_API_KEY to run this example.")
        raise SystemExit(1)
    console = Console()

    inner = Agent(
        "openai:gpt-5-nano",
        output_type=ArithmeticReport,
        system_prompt=(
            "You have add_inner. Call add_inner(10, 32) once. "
            "Your final output must have sum_value equal to that sum and product equal to sum_value*2."
        ),
        model_settings={"temperature": 0},
    )

    @inner.tool
    async def add_inner(ctx: RunContext, a: int, b: int) -> int:
        """Add two integers."""
        return a + b

    outer = Agent(
        "openai:gpt-5-nano",
        system_prompt=(
            "You have run_analyst and sidecar_ping. "
            "When the user wants the arithmetic report, you MUST call BOTH tools in the same step "
            "(parallel tool calls): "
            "(1) run_analyst with the user's message as `task`, "
            "(2) sidecar_ping with no arguments. "
            "Then answer using the analyst's structured result (mention sidecar if useful)."
        ),
        model_settings={"temperature": 0},
    )

    @outer.tool
    async def run_analyst(ctx: RunContext, task: str) -> ArithmeticReport:
        """Run the specialist and return its structured report."""
        result = await inner.run(task)
        if result.output is None:
            raise RuntimeError("inner agent produced no structured output")
        return result.output

    @outer.tool
    async def sidecar_ping(ctx: RunContext) -> str:
        """Cheap parallel sidecar; call in the same round as run_analyst."""
        return "parallel-sidecar-ok"

    adapted = wrap_pydantic_ai_agent(outer)
    r = await adapted.run_turn(
        "Produce the arithmetic report: sum of 10 and 32, then twice that sum; "
        "use add_inner inside the analyst. "
        "Validate parallel tools: call run_analyst and sidecar_ping together."
    )
    console.rule("[bold]Turn summary[/bold]")
    pprint({"status": r.status, "error": r.error, "output": r.output})
    console.rule("[bold]Event trace (tree)[/bold]")
    print_rich_event_trace(console, r.events)
    console.rule("[bold]Raw events (with children)[/bold]")
    for i, ev in enumerate(r.events):
        console.print(f"[dim]— root {i} —[/dim]")
        pprint(ev)
    console.print(
        "[dim]Expect sibling tools run_analyst and sidecar_ping under the root when batched. "
        "add_inner may appear under run_analyst if nested events are streamed.[/dim]"
    )


if __name__ == "__main__":
    asyncio.run(main())
