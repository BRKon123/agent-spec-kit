"""Fuzzing study scenario for T38."""
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
from tasks.fuzzing.scenarios.common import (
    FUZZ_TRIALS,
    FuzzTrial,
    fuzz_config_for_segment,
    fuzz_trial_cases,
    max_turns_for_segment,
)
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
TASK_ID = "T38"


def _scenario_facts(_store: TelcoStore) -> str:
    return (
        "- Your connection keeps lagging on and off.\n"
        "- You want thorough network diagnostics and confidence their systems are responding.\n"
    )

INTENT = "Run specialist diagnostics while handling status/heartbeat checks."
PERSONAS = [
    Persona(0, "patient_diagnostic_user", "patient", "Waits for diagnostics.", "reveal_upfront", "low"),
    Persona(1, "reassurance_seeking_user", "anxious", "Asks if agent is still there.", "reveal_when_prompted", "medium"),
    Persona(2, "technical_user", "technical", "Requests concise technical updates.", "reveal_when_prompted", "low"),
    Persona(3, "anxious_user", "anxious", "Worries chat has frozen.", "reveal_when_prompted", "medium"),
    Persona(4, "brief_response_user", "brief", "Wants short status updates only.", "reveal_when_prompted", "low"),
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
    yield build_user_simulator(
        llm_model=llm_model,
        prompt=build_user_prompt(
            task_id=TASK_ID,
            intent=INTENT,
            persona=persona,
            meta=store_us_t38.seed_meta,
            scenario_facts=_scenario_facts(store_us_t38),
        ),
    )
@ek.fixture
@ek.parametrize("fuzz_trial", fuzz_trial_cases(TASK_ID))
async def fuzz_trial_t38(fuzz_trial: FuzzTrial):
    yield fuzz_trial

@ek.scenario(
    agent_fixture="task_agent_us_t38",
    repeats=1,
    tags=("telecom", "fuzz-study", "task:T38", "method:manual", "oracle:F"),
)
async def test_t38_manual_fuzz_study(s, store_us_t38):
    bind_scenario_context("test_t38_manual_fuzz_study", variant="reference")
    from tasks.manual.test_T38 import test_t38_full
    await test_t38_full(s, store_us_t38)
@ek.scenario(
    agent_fixture="task_agent_us_t38",
    user_fixture="user_simulator_us_t38",
    repeats=1,
    tags=("telecom", "fuzz-study", "task:T38", "method:sim", "oracle:F"),
)
async def test_t38_sim_fuzz_study(s, store_us_t38):  # noqa: ARG001
    bind_scenario_context("test_t38_sim_fuzz_study", variant="reference")
    (
        s.simulate_conversation(
            seed_actor="user",
            seed_input=SIM_CHAT_OPEN,
            max_turns=5,
            stop_condition=sim_stop(
                "Assistant indicates network diagnostics are being run or reviewed.",
                "Assistant provides a status/heartbeat style progress acknowledgement.",
            ),
            stop_on_actor="agent",
        )
        .assert_output(m.string(min_len=5), actor="agent")
        .simulate_conversation(
            max_turns=7,
            stop_condition=sim_stop(
                "Assistant completed or summarized network diagnostics and line status.",
                "Assistant provided heartbeat or liveness-style progress without mutating account state.",
            ),
            stop_on_actor="agent",
        )
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
@ek.scenario(
    agent_fixture="task_agent_us_t38",
    repeats=1,
    tags=("telecom", "fuzz-study", "task:T38", "method:fuzz", "oracle:F"),
)
async def test_t38_fuzz_fuzz_study(s, store_us_t38, fuzz_trial_t38: FuzzTrial):
    bind_scenario_context("test_t38_fuzz_fuzz_study", variant="reference")
    cfg0 = fuzz_config_for_segment(task_id=TASK_ID, store=store_us_t38, fuzz_trial=fuzz_trial_t38, segment_index=0)
    cfg1 = fuzz_config_for_segment(task_id=TASK_ID, store=store_us_t38, fuzz_trial=fuzz_trial_t38, segment_index=1)
    (
        s.fuzz_conversation(
            fuzz_config=cfg0,
            trials=FUZZ_TRIALS,
            max_user_turns=max_turns_for_segment("T38", 0),
        )
        .assert_output(m.string(min_len=5), actor="agent")
        .fuzz_conversation(
            fuzz_config=cfg1,
            trials=FUZZ_TRIALS,
            max_user_turns=max_turns_for_segment("T38", 1),
        )
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
