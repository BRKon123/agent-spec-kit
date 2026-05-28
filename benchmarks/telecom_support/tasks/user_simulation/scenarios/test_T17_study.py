"""User simulation study scenario for T17."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import agent_spec_kit as ek
import agent_spec_kit.match as m

from agent_wrap import wrap_reference_agent
from store.store import TelcoStore
from tasks.specs import oracles as o
from tasks.specs import trace_oracles as to
from tasks.specs.run_context import bind_scenario_context
from tasks.user_simulation.scenarios.common import (
    SIM_CHAT_OPEN,
    Persona,
    build_user_prompt,
    build_user_simulator,
    cleanup_store,
    llm_model_cases,
    persona_cases,
    seeded_store,
    sim_stop,
)

TASK_ID = "T17"
INTENT = "Ask for compensation after a short outage."
PERSONAS = [
    Persona(0, "polite_compensation_asker", "polite", "Calmly asks if compensation is available.", "reveal_upfront", "low"),
    Persona(1, "angry_refund_demander", "angry", "Demands money back quickly.", "reveal_upfront", "high"),
    Persona(2, "policy_questioning_user", "analytical", "Requests policy explanation.", "reveal_when_prompted", "medium"),
    Persona(3, "comparison_user", "challenging", "Compares policy to competitors.", "reveal_when_prompted", "medium"),
    Persona(4, "accepts_alternative_help", "pragmatic", "Starts with compensation then accepts alternatives.", "reveal_when_prompted", "low"),
]


def _scenario_facts(store: TelcoStore) -> str:
    m = store.seed_meta
    return (
        f"- Service dropped out briefly yesterday near postcode {m['postcode']}.\n"
        "- You want to know if you are owed compensation.\n"
    )


@ek.fixture
async def store_us_t17():
    store = seeded_store(TASK_ID)
    try:
        yield store
    finally:
        cleanup_store(store)


@ek.fixture
async def task_agent_us_t17(store_us_t17):
    yield wrap_reference_agent(store_us_t17)


@ek.fixture
@ek.parametrize("llm_model", llm_model_cases())
@ek.parametrize("persona", persona_cases(PERSONAS))
async def user_simulator_us_t17(store_us_t17, llm_model: str, persona: Persona):
    yield build_user_simulator(
        llm_model=llm_model,
        prompt=build_user_prompt(
            task_id=TASK_ID,
            intent=INTENT,
            persona=persona,
            meta=store_us_t17.seed_meta,
            scenario_facts=_scenario_facts(store_us_t17),
        ),
    )


@ek.scenario(
    agent_fixture="task_agent_us_t17",
    repeats=1,
    tags=("telecom", "user-simulation", "task:T17", "method:manual", "oracle:F"),
)
async def test_t17_manual_study(s, store_us_t17):
    bind_scenario_context("test_t17_manual_study", variant="reference")
    from tasks.manual.test_T17 import test_t17_full

    await test_t17_full(s, store_us_t17)


@ek.scenario(
    agent_fixture="task_agent_us_t17",
    user_fixture="user_simulator_us_t17",
    repeats=1,
    tags=("telecom", "user-simulation", "task:T17", "method:sim", "oracle:F"),
)
async def test_t17_sim_study(s, store_us_t17):  # noqa: ARG001
    bind_scenario_context("test_t17_sim_study", variant="reference")
    (
        # manual_checkpoint_1 -> sim_segment_1:
        # Equivalent to early compensation-policy exchange before concluding eligibility.
        s.simulate_conversation(
            seed_actor="user",
            seed_input=SIM_CHAT_OPEN,
            max_turns=5,
            stop_condition=sim_stop(
                "Assistant discusses compensation eligibility or policy.",
                "Assistant does not promise a credit has been applied.",
            ),
            stop_on_actor="agent",
        )
        .assert_output(m.string(min_len=5), actor="agent")
        # manual_checkpoint_2 -> sim_segment_2:
        # Preserve full-oracle trace/state/output constraints at end of run.
        .simulate_conversation(
            max_turns=7,
            stop_condition=sim_stop(
                "Assistant explains the outage is too brief for compensation or refuses a bill credit.",
                "Assistant does not state that a credit or goodwill adjustment was applied.",
            ),
            stop_on_actor="agent",
        )
        .assert_tool_calls(
            [
                m.tool_call("authenticate_customer"),
                m.tool_call("run_billing_policy_specialist"),
            ],
            ordered=True,
            allow_extras=True,
            actor="agent",
            turn="up_to_now",
        )
        .forbid_tool_calls(to.CREDIT_FORBIDDEN, actor="agent", turn="up_to_now")
        .assert_that(lambda: o.assert_no_credit_rows(store_us_t17))
        .assert_output(
            m.llm_criteria(
                criteria=[
                    "Explains that a brief or short outage is not eligible for compensation or a bill credit",
                ],
                threshold=1,
                model="openai:gpt-5-nano",
            ),
            actor="agent",
            turn="up_to_now",
        )
    )
