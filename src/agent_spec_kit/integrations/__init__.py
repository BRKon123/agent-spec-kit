from __future__ import annotations

from typing import Any

__all__ = ["wrap_langchain_agent", "wrap_pydantic_ai_agent"]


def __getattr__(name: str) -> Any:
    if name == "wrap_langchain_agent":
        from agent_spec_kit.integrations.langchain_adapter import wrap_langchain_agent

        return wrap_langchain_agent
    if name == "wrap_pydantic_ai_agent":
        from agent_spec_kit.integrations.pydantic_ai_adapter import wrap_pydantic_ai_agent

        return wrap_pydantic_ai_agent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
