"""Shared helpers for hand-authored user simulation study scenarios."""

from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

import agent_spec_kit as ek
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from agent_spec_kit.integrations.langchain_adapter import wrap_langchain_agent
from store.seeds import apply_seed
from store.store import TelcoStore

_SIM_LLM_CASES = (
    ek.case("gpt-5-nano", id="gpt5nano"),
)

SIM_CHAT_OPEN = "[Mobile support chat connected.]"
SIM_STOP_MODEL = "openai:gpt-5-nano"


def sim_stop(*criteria: str, threshold: int = 1):
    """LLM judge for when a simulate_conversation segment has reached its stopping point."""
    import agent_spec_kit.match as m

    return m.llm_criteria(
        criteria=list(criteria),
        threshold=threshold,
        model=SIM_STOP_MODEL,
    )

REVEAL_UPFRONT = "reveal_upfront"
REVEAL_WHEN_PROMPTED = "reveal_when_prompted"

_DISCLOSURE_GLOSSARY = (
    "Disclosure (when you share facts from 'What you know', unless Behavior says otherwise):\n"
    f"- {REVEAL_UPFRONT}: volunteer relevant details (IDs, ticket refs, verification) in your opening messages.\n"
    f"- {REVEAL_WHEN_PROMPTED}: lead with the problem; share specifics when the agent asks or clearly needs them.\n"
    "If Behavior or scenario facts tell you not to reveal something (e.g. withhold a ticket id), follow that "
    "even when prompted—say you do not have it or cannot find it rather than inventing a value.\n"
)


@dataclass(frozen=True)
class Persona:
    seed: int
    name: str
    style: str
    behaviour: str
    disclosure_pattern: str
    pressure_level: str


def llm_model_cases() -> tuple[ek.Case[str], ...]:
    return _SIM_LLM_CASES


def require_api_key() -> None:
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        raise RuntimeError("User simulation scenarios require OPENAI_API_KEY.")


def seeded_store(task_id: str) -> TelcoStore:
    base = Path(tempfile.mkdtemp(prefix="telco_sim_study_"))
    telco = TelcoStore(base / "telco.sqlite")
    apply_seed(telco, f"task_{task_id}")
    return telco


def cleanup_store(store: TelcoStore) -> None:
    try:
        root = store.path.parent
    except Exception:
        return
    shutil.rmtree(root, ignore_errors=True)


def persona_cases(personas: list[Persona]) -> tuple[ek.Case[Persona], ...]:
    return tuple(
        ek.case(p, id=f"seed{p.seed}_{p.name}", name=f"seed={p.seed} {p.name}") for p in personas
    )


def _base_knowledge(meta: dict[str, object]) -> str:
    lines: list[str] = []
    for key in ("customer_id", "verification_token", "line_id", "postcode"):
        val = meta.get(key)
        if val is not None:
            lines.append(f"- {key}: {val}")
    return "\n".join(lines)


def build_user_prompt(
    *,
    task_id: str,
    intent: str,
    persona: Persona,
    meta: dict[str, object],
    scenario_facts: str = "",
) -> str:
    knowledge = _base_knowledge(meta)
    extra = scenario_facts.strip()
    if extra:
        knowledge = f"{knowledge}\n{extra}" if knowledge else extra

    prompt = (
        "You are simulating a mobile-network customer in a support conversation.\n"
        "You are ONLY the customer. Never act like the support agent.\n"
        f"Goal: {intent}\n"
        f"Persona name: {persona.name}\n"
        f"Style: {persona.style}\n"
        f"Behavior: {persona.behaviour}\n"
        f"Disclosure pattern: {persona.disclosure_pattern}\n"
        f"Pressure level: {persona.pressure_level}\n"
        "\n"
        "You are not following a script. Each turn, decide what to say from your goal, "
        "persona, disclosure pattern, and the conversation so far.\n"
        "\n"
        f"{_DISCLOSURE_GLOSSARY}\n"
        "You must stay plausible and goal-directed. Do not mention tools, tests, or oracles.\n"
        "Keep each response to 1-2 short sentences.\n"
        "\n"
        "Hard constraints:\n"
        "- Speak in first person as the customer.\n"
        "- Do not provide process plans or step-by-step workflows.\n"
        "- Do not say what YOU will run/check/escalate; that is the agent's role.\n"
        "- Do not ask the agent for customer_id/verification_token field names explicitly.\n"
        "- Do not repeat long structured bullet lists from the agent.\n"
        "- Do not use operator language like 'to proceed', 'I will now', 'next quick questions'.\n"
        "\n"
        "Style target:\n"
        "- Sound like a real customer texting support.\n"
        "- Short, natural language; occasional uncertainty is fine.\n"
        "- Keep focus on the issue and what you want help with.\n"
        "\n"
        "What you know (use these exact values only when you choose to share them):\n"
        f"{knowledge}\n"
        "When you mention an ID or token, use the exact value from 'What you know'. "
        "Do not invent alternatives.\n"
        "Before sending your response, self-check: 'Does this sound like a customer message, not an agent message?'\n"
    )
    return prompt


def build_user_simulator(*, llm_model: str, prompt: str):
    require_api_key()
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model=llm_model, temperature=0.3)
    graph = create_react_agent(llm, [], prompt=prompt)
    return wrap_langchain_agent(
        graph,
        lambda msg: {"messages": [HumanMessage(content=msg)]},
        stream_mode="updates",
        version="v2",
    )
