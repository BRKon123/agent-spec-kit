"""
Nested create_agent: event trace is a tree under one root ``AgentTurnEvent``.

Includes **parallel outer tools** (`run_specialist` + `sidecar_ping`) so one ``AIMessage``
can register two sibling ``ToolCallEvent`` nodes under the root. Inner specialist traffic
may still nest under ``run_specialist`` when the stream exposes it.
"""

from __future__ import annotations

import asyncio
import json
import os

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from rich.console import Console
from rich.pretty import pprint

from agent_spec_kit import print_rich_event_trace
from agent_spec_kit.integrations.langchain_adapter import wrap_langchain_agent


class ArithmeticReport(BaseModel):
    sum_value: int = Field(description="Result of add_integers_inner(10, 32)")
    product: int = Field(description="sum_value times 2")


async def main() -> None:
    if not os.environ.get("OPENAI_API_KEY"):
        print("Set OPENAI_API_KEY to run this example.")
        raise SystemExit(1)
    console = Console()
    model = ChatOpenAI(
        model="gpt-5-nano",
        temperature=0.1,
        timeout=30,
    )

    @tool
    def add_integers_inner(a: int, b: int) -> int:
        """Add two integers and return the sum."""
        return a + b

    specialist = create_agent(
        model,
        tools=[add_integers_inner],
        response_format=ArithmeticReport,
        system_prompt=(
            "You must call add_integers_inner with a=10 and b=32 exactly once. "
            "Set sum_value to that result and product to sum_value times 2."
        ),
    )

    @tool
    def run_specialist(task: str) -> str:
        """Delegate to the arithmetic specialist; returns JSON from its structured report."""
        out = specialist.invoke({"messages": [{"role": "user", "content": task}]})
        sr = out.get("structured_response")
        if sr is not None:
            if hasattr(sr, "model_dump_json"):
                return sr.model_dump_json()
            return json.dumps(sr) if isinstance(sr, dict) else str(sr)
        last = out["messages"][-1]
        content = getattr(last, "content", last)
        return str(content)

    @tool
    def sidecar_ping() -> str:
        """Cheap parallel sidecar; must be called in the same tool round as run_specialist."""
        return "parallel-sidecar-ok"

    main_graph = create_agent(
        model,
        tools=[run_specialist, sidecar_ping],
        system_prompt=(
            "You have run_specialist and sidecar_ping. "
            "When the user wants the arithmetic report, you MUST request BOTH tools in the "
            "same model step (parallel tool calls): "
            "(1) run_specialist with the user's message verbatim as `task`, "
            "(2) sidecar_ping with no arguments. "
            "Then answer the user using the specialist JSON (mention sidecar token if useful)."
        ),
    )

    adapted = wrap_langchain_agent(
        main_graph,
        lambda msg: {"messages": [HumanMessage(content=msg)]},
        stream_mode="updates",
        version="v2",
        subgraphs=True,
    )
    r = await adapted.run_turn(
        "Produce the arithmetic report: sum of 10 and 32, then product of that sum with 2. "
        "Also validate parallel tools: invoke run_specialist and sidecar_ping together."
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
        "[dim]Under the root turn you should see sibling tools run_specialist and sidecar_ping "
        "when the model batches them. Inner add_integers_inner may appear under run_specialist "
        "if the stream includes it.[/dim]"
    )


if __name__ == "__main__":
    asyncio.run(main())
