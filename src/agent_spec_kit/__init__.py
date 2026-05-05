"""Agent specification kit — build and validate agent configs."""

from __future__ import annotations

from typing import Any

from agent_spec_kit.events import (
    AgentEvent,
    AgentTurnEvent,
    BaseEvent,
    ToolCallEvent,
    UserTurnEvent,
    new_event_id,
    print_rich_event_trace,
)
from agent_spec_kit.decorators import fixture, parametrize, scenario
from agent_spec_kit.failures import Counterexample, FailureRecord, ScenarioAssertionFailed
from agent_spec_kit.param_cases import Case, case
from agent_spec_kit.run import AdaptedAgent, ConversationTurn, TurnResult
from agent_spec_kit.fuzz_config import ExtractionConfig, FuzzConfig, ShrinkConfig
from agent_spec_kit.scenario_core import Scenario, create_scenario

__all__ = [
    "AdaptedAgent",
    "Case",
    "case",
    "parametrize",
    "AgentEvent",
    "AgentTurnEvent",
    "BaseEvent",
    "ToolCallEvent",
    "UserTurnEvent",
    "ConversationTurn",
    "TurnResult",
    "Scenario",
    "create_scenario",
    "Counterexample",
    "FailureRecord",
    "ScenarioAssertionFailed",
    "fixture",
    "scenario",
    "__version__",
    "new_event_id",
    "print_rich_event_trace",
    "wrap_langchain_agent",
    "wrap_pydantic_ai_agent",
    "match",
    "fuzz",
    "shrink",
    "FuzzConfig",
    "ShrinkConfig",
    "ExtractionConfig",
]

__version__ = "0.1.0"


def __getattr__(name: str) -> Any:
    if name == "match":
        import agent_spec_kit.match as match_mod

        return match_mod
    if name == "wrap_langchain_agent":
        from agent_spec_kit.integrations.langchain_adapter import wrap_langchain_agent

        return wrap_langchain_agent
    if name == "wrap_pydantic_ai_agent":
        from agent_spec_kit.integrations.pydantic_ai_adapter import wrap_pydantic_ai_agent

        return wrap_pydantic_ai_agent
    if name == "fuzz":
        import agent_spec_kit.fuzz as fuzz_mod

        return fuzz_mod
    if name == "shrink":
        import agent_spec_kit.shrink as shrink_mod

        return shrink_mod
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
