"""Fuzzing study scenario for T35."""
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
TASK_ID = "T35"


def _scenario_facts(store: TelcoStore) -> str:
    meta = store.seed_meta
    tid = meta.get("existing_ticket_id", "TCK-EXIST-01")
    return (
        f"- existing_ticket_id: {tid}\n"
        "- You want that open ticket escalated, not a duplicate created.\n"
    )

INTENT = "Escalate an existing ticket without creating duplicates."
PERSONAS = [
    Persona(0, "has_ticket_reference_ready", "prepared", "Provides ticket id immediately.", "reveal_upfront", "low"),
    Persona(
        1,
        "does_not_know_ticket_id",
        "uncertain",
        "Says previous support exists; withholds ticket id until asked, then may say you cannot find it.",
        "reveal_when_prompted",
        "low",
    ),
    Persona(
        2,
        "frustrated_repeat_caller",
        "frustrated",
        "Mentions repeated explanations; gives ticket id when agent asks for reference.",
        "reveal_when_prompted",
        "medium",
    ),
    Persona(3, "wants_manager_escalation", "pressure", "Asks for manager escalation quickly.", "reveal_upfront", "high"),
    Persona(4, "detail_heavy_user", "detailed", "Provides chronology and prior advice.", "reveal_upfront", "low"),
]
@ek.fixture
async def store_us_t35():
    store = seeded_store(TASK_ID)
    try:
        yield store
    finally:
        cleanup_store(store)
@ek.fixture
async def task_agent_us_t35(store_us_t35):
    yield wrap_reference_agent(store_us_t35)
@ek.fixture
@ek.parametrize("llm_model", llm_model_cases())
@ek.parametrize("persona", persona_cases(PERSONAS))
async def user_simulator_us_t35(store_us_t35, llm_model: str, persona: Persona):
    yield build_user_simulator(
        llm_model=llm_model,
        prompt=build_user_prompt(
            task_id=TASK_ID,
            intent=INTENT,
            persona=persona,
            meta=store_us_t35.seed_meta,
            scenario_facts=_scenario_facts(store_us_t35),
        ),
    )
@ek.fixture
@ek.parametrize("fuzz_trial", fuzz_trial_cases(TASK_ID))
async def fuzz_trial_t35(fuzz_trial: FuzzTrial):
    yield fuzz_trial

@ek.scenario(
    agent_fixture="task_agent_us_t35",
    repeats=1,
    tags=("telecom", "fuzz-study", "task:T35", "method:manual", "oracle:F"),
)
async def test_t35_manual_fuzz_study(s, store_us_t35):
    bind_scenario_context("test_t35_manual_fuzz_study", variant="reference")
    from tasks.manual.test_T35 import test_t35_full
    await test_t35_full(s, store_us_t35)
@ek.scenario(
    agent_fixture="task_agent_us_t35",
    user_fixture="user_simulator_us_t35",
    repeats=1,
    tags=("telecom", "fuzz-study", "task:T35", "method:sim", "oracle:F"),
)
async def test_t35_sim_fuzz_study(s, store_us_t35):  # noqa: ARG001
    bind_scenario_context("test_t35_sim_fuzz_study", variant="reference")
    (
        s.simulate_conversation(
            seed_actor="user",
            seed_input=SIM_CHAT_OPEN,
            max_turns=5,
            stop_condition=sim_stop(
                "Assistant discusses existing ticket reference or escalation path.",
                "Assistant has not yet confirmed a duplicate new ticket was created.",
            ),
            stop_on_actor="agent",
        )
        .assert_output(m.string(min_len=5), actor="agent")
        .simulate_conversation(
            max_turns=7,
            stop_condition=sim_stop(
                "Assistant confirms the existing ticket was escalated or states a clear escalation outcome.",
                "Assistant has not created a duplicate new ticket.",
            ),
            stop_on_actor="agent",
        )
        .assert_tool_calls(
            [
                m.tool_call("authenticate_customer"),
                m.tool_call("escalate_ticket"),
            ],
            ordered=True,
            allow_extras=True,
            actor="agent",
            turn="up_to_now",
        )
        .assert_that(lambda: o.assert_ticket_count(store_us_t35, 1))
        .assert_output(
            to.ticket_escalation_output(store_us_t35),
            actor="agent",
            turn="up_to_now",
        )
    )
@ek.scenario(
    agent_fixture="task_agent_us_t35",
    repeats=1,
    tags=("telecom", "fuzz-study", "task:T35", "method:fuzz", "oracle:F"),
)
async def test_t35_fuzz_fuzz_study(s, store_us_t35, fuzz_trial_t35: FuzzTrial):
    bind_scenario_context("test_t35_fuzz_fuzz_study", variant="reference")
    cfg0 = fuzz_config_for_segment(task_id=TASK_ID, store=store_us_t35, fuzz_trial=fuzz_trial_t35, segment_index=0)
    cfg1 = fuzz_config_for_segment(task_id=TASK_ID, store=store_us_t35, fuzz_trial=fuzz_trial_t35, segment_index=1)
    (
        s.fuzz_conversation(
            fuzz_config=cfg0,
            trials=FUZZ_TRIALS,
            max_user_turns=max_turns_for_segment("T35", 0),
        )
        .assert_output(m.string(min_len=5), actor="agent")
        .fuzz_conversation(
            fuzz_config=cfg1,
            trials=FUZZ_TRIALS,
            max_user_turns=max_turns_for_segment("T35", 1),
        )
        .assert_tool_calls(
            [
                m.tool_call("authenticate_customer"),
                m.tool_call("escalate_ticket"),
            ],
            ordered=True,
            allow_extras=True,
            actor="agent",
            turn="up_to_now",
        )
        .assert_that(lambda: o.assert_ticket_count(store_us_t35, 1))
        .assert_output(
            to.ticket_escalation_output(store_us_t35),
            actor="agent",
            turn="up_to_now",
        )
    )
