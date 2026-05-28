"""User simulation study scenario for T03 (optional interesting case)."""
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
from tasks.user_simulation.scenarios.common import Persona, build_user_prompt, build_user_simulator, cleanup_store, llm_model_cases, persona_cases, seeded_store
TASK_ID = "T03"
INTENT = "Troubleshoot before escalation for persistent data failure."
PERSONAS = [
    Persona(0, "cooperative_non_technical", "cooperative", "Follows troubleshooting steps.", "clarifies_after_prompt", "low"),
    Persona(1, "impatient_escalation_seeker", "impatient", "Pushes for ticket early.", "early_full", "high"),
    Persona(2, "partial_information_user", "vague", "Shares details only after prompts.", "minimal_then_expand", "medium"),
    Persona(3, "confused_device_focused_user", "confused", "Asks if device itself is broken.", "progressive", "medium"),
    Persona(4, "cautious_user_waiting_for_call", "cautious", "Resists restart due to expected call.", "progressive", "medium"),
]
@ek.fixture
async def store_us_t03():
    store = seeded_store(TASK_ID)
    try:
        yield store
    finally:
        cleanup_store(store)
@ek.fixture
async def task_agent_us_t03(store_us_t03):
    yield wrap_reference_agent(store_us_t03)
@ek.fixture
@ek.parametrize("llm_model", llm_model_cases())
@ek.parametrize("persona", persona_cases(PERSONAS))
async def user_simulator_us_t03(store_us_t03, llm_model: str, persona: Persona):
    yield build_user_simulator(llm_model=llm_model, prompt=build_user_prompt(task_id=TASK_ID, intent=INTENT, persona=persona, meta=store_us_t03.seed_meta))
@ek.scenario(agent_fixture="task_agent_us_t03", repeats=1, tags=("telecom", "user-simulation", "task:T03", "method:manual", "oracle:F", "interesting"))
async def test_t03_manual_study(s, store_us_t03):
    bind_scenario_context("test_t03_manual_study", variant="reference")
    from tasks.manual.test_T03 import test_t03_full
    await test_t03_full(s, store_us_t03)
@ek.scenario(agent_fixture="task_agent_us_t03", user_fixture="user_simulator_us_t03", repeats=1, tags=("telecom", "user-simulation", "task:T03", "method:sim", "oracle:F", "interesting"))
async def test_t03_sim_study(s, store_us_t03):  # noqa: ARG001
    bind_scenario_context("test_t03_sim_study", variant="reference")
    (
        s.simulate_conversation(
            seed_actor="user",
            seed_input="Session start. Explain your support request.",
            max_turns=4,
            stop_condition=m.all_of(
                m.one_of(m.contains("restart"), m.contains("troubleshoot")),
                m.one_of(m.contains("verify"), m.contains("line")),
            ),
            stop_on_actor="agent",
        )
        .assert_output(m.string(min_len=5), actor="agent")
        .simulate_conversation(max_turns=6)
        .assert_tool_calls([], ordered=True, allow_extras=True, actor="agent", turn="up_to_now")
        .assert_output(m.string(min_len=20), actor="agent", turn="up_to_now")
    )
