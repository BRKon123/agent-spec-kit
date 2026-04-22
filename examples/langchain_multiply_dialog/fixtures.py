"""Live-only LangGraph agents for multiplication tutor + simulated student.

Set ``OPENAI_API_KEY`` before ``agent-spec-kit run`` on this directory. The tutor
exposes only ``multiply_integers``; the user side is either a tool-free react agent
or a react agent that calls ``student_checkpoint`` on every student turn (see
``user_simulator_with_tools``).
"""

from __future__ import annotations

import os

import agent_spec_kit as ek
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from agent_spec_kit.integrations.langchain_adapter import wrap_langchain_agent

_LLM_MODEL_CASES = (
    ek.case("gpt-4.1-nano-2025-04-14", id="gpt41nano"),
    ek.case("gpt-5-nano", id="gpt5nano"),
)

_TUTOR_SYSTEM = (
    "You are a math tutor with one tool: multiply_integers(a, b). "
    "Whenever the user asks for a product of two integers, call multiply_integers "
    "with those integers (use argument names a and b). "
    "Then answer in plain language and include the numeric product as digits."
)

_USER_SYSTEM = (
    "You are a student practising multiplication with a tutor. "
    "Each reply must be exactly one short sentence and nothing else: a single "
    "multiplication question using two positive integers under 20. "
    "When the incoming message is a session start cue (contains 'Session start'), "
    "your reply must be exactly: What is 4 times 5? "
    "When the incoming message is the tutor's answer to that question, "
    "your reply must be exactly: What is 3 times 9? "
    "Do not add greetings, explanations, or punctuation beyond a single question mark."
)

_USER_SYSTEM_WITH_TOOLS = (
    "You are a student practising multiplication with a tutor. "
    "On EVERY reply you MUST call the tool student_checkpoint exactly once before "
    "you answer: use phase='first' for your first substantive message after a session "
    "start cue, and phase='second' for your next message after you have seen the tutor's "
    "reply to your first question. "
    "After calling the tool, output exactly one short sentence and nothing else — "
    "a single multiplication question using two positive integers under 20. "
    "When the incoming message contains 'Session start', call student_checkpoint with "
    "phase='first' then say exactly: What is 4 times 5? "
    "When the incoming message is the tutor's answer to that question, call "
    "student_checkpoint with phase='second' then say exactly: What is 3 times 8? "
    "Do not add greetings, explanations, or punctuation beyond a single question mark."
)


def _require_api_key() -> None:
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        raise RuntimeError(
            "langchain_multiply_dialog requires OPENAI_API_KEY "
            "(live-only example; no offline graph)."
        )


@tool
def multiply_integers(a: int, b: int) -> int:
    """Multiply two integers and return the product."""
    return a * b


@tool
def student_checkpoint(phase: str) -> str:
    """Record which student reply this is; phase is 'first' or 'second'."""
    return phase


def _tutor_graph(llm_model: str) -> object:
    _require_api_key()
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model=llm_model, temperature=0)
    return create_react_agent(llm, [multiply_integers], prompt=_TUTOR_SYSTEM)


def _user_graph(llm_model: str) -> object:
    _require_api_key()
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model=llm_model, temperature=0)
    return create_react_agent(llm, [], prompt=_USER_SYSTEM)


def _user_graph_with_tools(llm_model: str) -> object:
    _require_api_key()
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model=llm_model, temperature=0)
    return create_react_agent(llm, [student_checkpoint], prompt=_USER_SYSTEM_WITH_TOOLS)


@ek.fixture
@ek.parametrize("llm_model", _LLM_MODEL_CASES)
async def adapted_agent(llm_model: str):
    graph = _tutor_graph(llm_model)
    return wrap_langchain_agent(
        graph,
        lambda msg: {"messages": [HumanMessage(content=msg)]},
        stream_mode="updates",
        version="v2",
    )


@ek.fixture
@ek.parametrize("llm_model", _LLM_MODEL_CASES)
async def user_simulator(llm_model: str):
    graph = _user_graph(llm_model)
    return wrap_langchain_agent(
        graph,
        lambda msg: {"messages": [HumanMessage(content=msg)]},
        stream_mode="updates",
        version="v2",
    )


@ek.fixture
@ek.parametrize("llm_model", _LLM_MODEL_CASES)
async def user_simulator_with_tools(llm_model: str):
    graph = _user_graph_with_tools(llm_model)
    return wrap_langchain_agent(
        graph,
        lambda msg: {"messages": [HumanMessage(content=msg)]},
        stream_mode="updates",
        version="v2",
    )
