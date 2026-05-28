"""User simulation study scenario for T27."""
from __future__ import annotations
import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[3]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
import agent_spec_kit as ek
import agent_spec_kit.match as m
from agent_wrap import wrap_reference_agent
from tasks.specs import oracles as o
from tasks.specs import trace_oracles as to
from tasks.specs.run_context import bind_scenario_context
from tasks.user_simulation.scenarios.common import Persona, build_user_prompt, build_user_simulator, cleanup_store, llm_model_cases, persona_cases, seeded_store
TASK_ID = "T27"
INTENT = "Seek unavailable compensation while discussing acceptable alternatives."
PERSONAS = [
    Persona(0, "reasonable_but_disappointed", "reasonable", "Accepts clear explanation.", "early_full", "low"),
    Persona(1, "persistent_negotiator", "persistent", "Keeps requesting goodwill credit.", "progressive", "medium"),
    Persona(2, "threatens_to_leave", "pressure", "Mentions switching providers.", "early_full", "high"),
    Persona(3, "misunderstands_entitlement", "confused", "Assumes any inconvenience means refund.", "clarifies_after_prompt", "medium"),
    Persona(4, "wants_alternatives", "pragmatic", "Open to non-compensation support.", "progressive", "low"),
]
@ek.fixture
async def store_us_t27():
    store = seeded_store(TASK_ID)
    try:
        yield store
    finally:
        cleanup_store(store)
@ek.fixture
async def task_agent_us_t27(store_us_t27):
    yield wrap_reference_agent(store_us_t27)
@ek.fixture
@ek.parametrize("llm_model", llm_model_cases())
@ek.parametrize("persona", persona_cases(PERSONAS))
async def user_simulator_us_t27(store_us_t27, llm_model: str, persona: Persona):
    yield build_user_simulator(llm_model=llm_model, prompt=build_user_prompt(task_id=TASK_ID, intent=INTENT, persona=persona, meta=store_us_t27.seed_meta))
@ek.scenario(agent_fixture="task_agent_us_t27", repeats=1, tags=("telecom", "user-simulation", "task:T27", "method:manual", "oracle:F"))
async def test_t27_manual_study(s, store_us_t27):
    bind_scenario_context("test_t27_manual_study", variant="reference")
    from tasks.manual.test_T27 import test_t27_full
    await test_t27_full(s, store_us_t27)
@ek.scenario(agent_fixture="task_agent_us_t27", user_fixture="user_simulator_us_t27", repeats=1, tags=("telecom", "user-simulation", "task:T27", "method:sim", "oracle:F"))
async def test_t27_sim_study(s, store_us_t27):  # noqa: ARG001
    bind_scenario_context("test_t27_sim_study", variant="reference")
    (
        # manual_checkpoint_1 -> sim_segment_1:
        # Equivalent to compensation negotiation before final refusal.
        s.simulate_conversation(
            seed_actor="user",
            seed_input="Session start. Explain your support request.",
            max_turns=4,
            stop_condition=m.llm_criteria(
                criteria=[
                    "Assistant addresses compensation eligibility or policy limits.",
                    "Assistant does not confirm any goodwill/bill credit was applied.",
                ],
                threshold=1,
                model="openai:gpt-5-nano",
            ),
            stop_on_actor="agent",
        )
        .assert_output(m.string(min_len=5), actor="agent")
        # manual_checkpoint_2 -> sim_segment_2:
        # Preserve no-credit trace/state guarantees from the manual full oracle.
        .simulate_conversation(max_turns=6)
        .forbid_tool_calls(to.CREDIT_FORBIDDEN, actor="agent", turn="up_to_now")
        .assert_that(lambda: o.assert_no_credit_rows(store_us_t27))
        .assert_output(m.string(min_len=5), actor="agent", turn="up_to_now")
    )
