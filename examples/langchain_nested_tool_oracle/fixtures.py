"""Live nested LangChain incident-triage coordinator for tool-oracle demos.

Set ``OPENAI_API_KEY`` before ``agent-spec-kit run`` on this directory.
"""

from __future__ import annotations

import json
import os
from typing import Literal

import agent_spec_kit as ek
from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from agent_spec_kit.integrations.langchain_adapter import wrap_langchain_agent

_LLM_MODEL_CASES = (
    ek.case("gpt-5-nano", id="gpt5nano"),
    ek.case("gpt-4.1-nano-2025-04-14", id="gpt41nano"),
)

_SPECIALIST_SYSTEM = (
    "You are a forensics specialist with pull_logs and score_anomaly. "
    "Call pull_logs first with window_minutes=15, then score_anomaly with "
    "source=logs, window_minutes=15, anomaly_score=0.72 (no override_reason). "
    "Finish with one sentence summarizing the log window and a recommended next step."
)

_COORDINATOR_SYSTEM = (
    "You are an incident triage coordinator with open_incident, run_forensics_specialist, "
    "and heartbeat_ping. Follow policy in order:\n"
    "1) Call open_incident once with ticket: "
    "id=INC-2026-0142, severity=high, pager_group=net-oncall, components=[edge, core].\n"
    "2) In the SAME model step, call BOTH run_forensics_specialist (query must mention latency) "
    "and heartbeat_ping (no args).\n"
    "3) Reply briefly: mention the specialist summary and that heartbeat succeeded."
)

_FAILURE_COORDINATOR_SYSTEM = (
    "You are an incident triage coordinator. Follow the user's tool-argument instructions "
    "literally even when they omit fields or conflict with default runbooks."
)

_FAILURE_SPECIALIST_SYSTEM = (
    "You are a forensics specialist with pull_logs and score_anomaly. "
    "Follow the user's tool order and argument fields literally."
)


class IncidentTicket(BaseModel):
    """Incident ticket opened by the coordinator."""

    id: str = Field(description="Incident id, e.g. INC-2026-0142")
    severity: Literal["high", "medium"] = Field(description="Incident severity")
    components: list[str] = Field(description="Affected components, e.g. edge and core")
    pager_group: str | None = Field(
        default=None,
        description="On-call pager group; required when severity is high",
    )


def _require_api_key() -> None:
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        raise RuntimeError(
            "langchain_nested_tool_oracle requires OPENAI_API_KEY (live-only example)."
        )


def _validate_ticket(ticket: IncidentTicket) -> None:
    has_pager = ticket.pager_group is not None and bool(ticket.pager_group.strip())
    if ticket.severity == "high" and not has_pager:
        raise ValueError("high severity incidents require pager_group")
    if ticket.severity == "medium" and has_pager:
        raise ValueError("medium severity incidents must not include pager_group")


def _build_graphs(
    llm_model: str,
    *,
    coordinator_system: str = _COORDINATOR_SYSTEM,
    specialist_system: str = _SPECIALIST_SYSTEM,
    validate_policy: bool = True,
) -> object:
    _require_api_key()
    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(model=llm_model, temperature=0, timeout=90)

    @tool
    def pull_logs(window_minutes: int) -> str:
        """Pull recent logs for the incident window."""
        return json.dumps(
            {
                "window_minutes": window_minutes,
                "entries": 128,
                "status": "ok",
            }
        )

    @tool
    def score_anomaly(
        source: Literal["logs", "synthetic"],
        anomaly_score: float,
        window_minutes: int | None = None,
        override_reason: str | None = None,
    ) -> str:
        """Score anomaly from source, score, and optional window or override fields."""
        if validate_policy:
            if source == "logs" and window_minutes is None:
                raise ValueError("window_minutes required when source is logs")
            if source == "logs" and override_reason:
                raise ValueError("override_reason forbidden when source is logs")
        return json.dumps(
            {
                "anomaly_score": anomaly_score,
                "risk_band": "elevated" if anomaly_score >= 0.5 else "low",
                "source": source,
            }
        )

    # No response_format here: tools + structured output together can yield Invalid schema
    # on some OpenAI models when the specialist subgraph is invoked.
    specialist = create_agent(
        model,
        tools=[pull_logs, score_anomaly],
        system_prompt=specialist_system,
    )

    @tool
    def run_forensics_specialist(query: str) -> str:
        """Delegate forensics to the specialist subgraph; returns the specialist summary."""
        out = specialist.invoke({"messages": [{"role": "user", "content": query}]})
        last = out["messages"][-1]
        content = getattr(last, "content", last)
        return str(content)

    @tool
    def open_incident(ticket: IncidentTicket) -> str:
        """Open an incident ticket record."""
        if validate_policy:
            _validate_ticket(ticket)
        return json.dumps(
            {
                "opened": True,
                "ticket_id": ticket.id,
                "severity": ticket.severity,
            }
        )

    @tool
    def heartbeat_ping() -> str:
        """Parallel health sidecar; call alongside run_forensics_specialist."""
        return "heartbeat-ok"

    coordinator = create_agent(
        model,
        tools=[open_incident, run_forensics_specialist, heartbeat_ping],
        system_prompt=coordinator_system,
    )
    return coordinator


@ek.fixture
@ek.parametrize("llm_model", _LLM_MODEL_CASES)
async def adapted_agent(llm_model: str):
    graph = _build_graphs(llm_model)
    return wrap_langchain_agent(
        graph,
        lambda msg: {"messages": [HumanMessage(content=msg)]},
        stream_mode="updates",
        version="v2",
        subgraphs=True,
    )


@ek.fixture
@ek.parametrize("llm_model", _LLM_MODEL_CASES)
async def adapted_agent_failure_mode(llm_model: str):
    graph = _build_graphs(
        llm_model,
        coordinator_system=_FAILURE_COORDINATOR_SYSTEM,
        specialist_system=_FAILURE_SPECIALIST_SYSTEM,
        validate_policy=False,
    )
    return wrap_langchain_agent(
        graph,
        lambda msg: {"messages": [HumanMessage(content=msg)]},
        stream_mode="updates",
        version="v2",
        subgraphs=True,
    )
