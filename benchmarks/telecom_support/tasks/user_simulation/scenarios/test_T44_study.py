"""User simulation study scenario for T44 (optional interesting case)."""
from __future__ import annotations
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
import agent_spec_kit as ek
import agent_spec_kit.match as m
from agent_wrap import wrap_reference_agent
from tasks.specs.run_context import bind_scenario_context
from store.store import TelcoStore
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
TASK_ID = "T44"


def _scenario_facts(_store: TelcoStore) -> str:
    return (
        "- Mobile data still does not work.\n"
        "- You may have toggled airplane mode earlier; you are not sure it helped.\n"
        "- You have not restarted yet because you are waiting on an important call.\n"
        "- You want the next troubleshooting step, not a ticket or escalation yet.\n"
    )

INTENT = "Handle contradiction about restart and avoid premature escalation."
PERSONAS = [
    Persona(0, "honest_but_late_admission", "correcting", "Admits restart claim was inaccurate.", "reveal_when_prompted", "low"),
    Persona(1, "avoids_restart_due_to_call", "cautious", "Defers restart due to important call.", "reveal_when_prompted", "medium"),
    Persona(2, "embarrassed_correction", "apologetic", "Says yes too quickly, then corrects.", "reveal_when_prompted", "low"),
    Persona(3, "pushes_escalation_anyway", "pushy", "Demands escalation despite not restarting.", "reveal_when_prompted", "high"),
    Persona(4, "misunderstands_restart", "confused", "Thought lock/unlock was restart.", "reveal_when_prompted", "medium"),
]
@ek.fixture
async def store_us_t44():
    store = seeded_store(TASK_ID)
    try:
        yield store
    finally:
        cleanup_store(store)
@ek.fixture
async def task_agent_us_t44(store_us_t44):
    yield wrap_reference_agent(store_us_t44)
@ek.fixture
@ek.parametrize("llm_model", llm_model_cases())
@ek.parametrize("persona", persona_cases(PERSONAS))
async def user_simulator_us_t44(store_us_t44, llm_model: str, persona: Persona):
    yield build_user_simulator(
        llm_model=llm_model,
        prompt=build_user_prompt(
            task_id=TASK_ID,
            intent=INTENT,
            persona=persona,
            meta=store_us_t44.seed_meta,
            scenario_facts=_scenario_facts(store_us_t44),
        ),
    )
@ek.scenario(agent_fixture="task_agent_us_t44", repeats=1, tags=("telecom", "user-simulation", "task:T44", "method:manual", "oracle:F", "interesting"))
async def test_t44_manual_study(s, store_us_t44):
    bind_scenario_context("test_t44_manual_study", variant="reference")
    from tasks.manual.test_T44 import test_t44_full
    await test_t44_full(s, store_us_t44)
@ek.scenario(agent_fixture="task_agent_us_t44", user_fixture="user_simulator_us_t44", repeats=1, tags=("telecom", "user-simulation", "task:T44", "method:sim", "oracle:F", "interesting"))
async def test_t44_sim_study(s, store_us_t44):  # noqa: ARG001
    bind_scenario_context("test_t44_sim_study", variant="reference")
    (
        s.simulate_conversation(
            seed_actor="user",
            seed_input=SIM_CHAT_OPEN,
            max_turns=5,
            stop_condition=sim_stop(
                "Assistant asks or confirms restart/troubleshooting status",
                "Assistant avoids prematurely committing to escalation",
            ),
            stop_on_actor="agent",
        )
        .assert_output(m.string(min_len=5), actor="agent")
        .simulate_conversation(
            max_turns=6,
            stop_condition=sim_stop(
                "Assistant gave a concrete troubleshooting step without opening a ticket or escalating.",
                "The user's restart or device status concern was addressed in the reply.",
            ),
            stop_on_actor="agent",
        )
        .assert_tool_calls([], ordered=True, allow_extras=True, actor="agent", turn="up_to_now")
        .assert_output(m.string(min_len=20), actor="agent", turn="up_to_now")
    )
