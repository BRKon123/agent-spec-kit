"""User simulation study scenario for T38."""
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
from tasks.user_simulation.scenarios.common import (
    Persona,
    build_user_prompt,
    build_user_simulator,
    cleanup_store,
    llm_model_cases,
    persona_cases,
    seeded_store,
)
TASK_ID = "T38"
INTENT = "Run specialist diagnostics while handling status/heartbeat checks."
PERSONAS = [
    Persona(0, "patient_diagnostic_user", "patient", "Waits for diagnostics.", "early_full", "low"),
    Persona(1, "reassurance_seeking_user", "anxious", "Asks if agent is still there.", "progressive", "medium"),
    Persona(2, "technical_user", "technical", "Requests concise technical updates.", "progressive", "low"),
    Persona(3, "anxious_user", "anxious", "Worries chat has frozen.", "progressive", "medium"),
    Persona(4, "brief_response_user", "brief", "Wants short status updates only.", "minimal_then_expand", "low"),
]
@ek.fixture
async def store_us_t38():
    store = seeded_store(TASK_ID)
    try:
        yield store
    finally:
        cleanup_store(store)
@ek.fixture
async def task_agent_us_t38(store_us_t38):
    yield wrap_reference_agent(store_us_t38)
@ek.fixture
@ek.parametrize("llm_model", llm_model_cases())
@ek.parametrize("persona", persona_cases(PERSONAS))
async def user_simulator_us_t38(store_us_t38, llm_model: str, persona: Persona):
    yield build_user_simulator(llm_model=llm_model, prompt=build_user_prompt(task_id=TASK_ID, intent=INTENT, persona=persona, meta=store_us_t38.seed_meta))
@ek.scenario(
    agent_fixture="task_agent_us_t38",
    repeats=1,
    tags=("telecom", "user-simulation", "task:T38", "method:manual", "oracle:F"),
)
async def test_t38_manual_study(s, store_us_t38):
    bind_scenario_context("test_t38_manual_study", variant="reference")
    from tasks.manual.test_T38 import test_t38_full
    await test_t38_full(s, store_us_t38)
@ek.scenario(
    agent_fixture="task_agent_us_t38",
    user_fixture="user_simulator_us_t38",
    repeats=1,
    tags=("telecom", "user-simulation", "task:T38", "method:sim", "oracle:F"),
)
async def test_t38_sim_study(s, store_us_t38):  # noqa: ARG001
    bind_scenario_context("test_t38_sim_study", variant="reference")
    (
        # manual_checkpoint_1 -> sim_segment_1:
        # Equivalent to early network-diagnostic + liveness/status exchange.
        s.simulate_conversation(
            seed_actor="user",
            seed_input="Session start. Explain your support request.",
            max_turns=4,
            stop_condition=m.llm_criteria(
                criteria=[
                    "Assistant indicates network diagnostics are being run or reviewed.",
                    "Assistant provides a status/heartbeat style progress acknowledgement.",
                ],
                threshold=1,
                model="openai:gpt-5-nano",
            ),
            stop_on_actor="agent",
        )
        .assert_output(m.string(min_len=5), actor="agent")
        # manual_checkpoint_2 -> sim_segment_2:
        # Preserve full trace and no-mutation guarantees after diagnostics path completes.
        .simulate_conversation(max_turns=6)
        .assert_tool_calls(
            [
                m.tool_call("authenticate_customer"),
                to.network_specialist_children(),
                m.tool_call("heartbeat_ping"),
            ],
            ordered=True,
            allow_extras=True,
            actor="agent",
            turn="up_to_now",
        )
        .assert_that(lambda: o.assert_no_mutations(store_us_t38))
        .assert_output(m.string(min_len=5), actor="agent", turn="up_to_now")
    )
