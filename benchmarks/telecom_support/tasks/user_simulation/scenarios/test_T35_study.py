"""User simulation study scenario for T35."""
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
TASK_ID = "T35"


def _scenario_facts(store: TelcoStore) -> str:
    m = store.seed_meta
    tid = m.get("existing_ticket_id", "TCK-EXIST-01")
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
@ek.scenario(
    agent_fixture="task_agent_us_t35",
    repeats=1,
    tags=("telecom", "user-simulation", "task:T35", "method:manual", "oracle:F"),
)
async def test_t35_manual_study(s, store_us_t35):
    bind_scenario_context("test_t35_manual_study", variant="reference")
    from tasks.manual.test_T35 import test_t35_full
    await test_t35_full(s, store_us_t35)
@ek.scenario(
    agent_fixture="task_agent_us_t35",
    user_fixture="user_simulator_us_t35",
    repeats=1,
    tags=("telecom", "user-simulation", "task:T35", "method:sim", "oracle:F"),
)
async def test_t35_sim_study(s, store_us_t35):  # noqa: ARG001
    bind_scenario_context("test_t35_sim_study", variant="reference")
    (
        # manual_checkpoint_1 -> sim_segment_1:
        # Equivalent to identifying existing ticket/escalation context.
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
        # manual_checkpoint_2 -> sim_segment_2:
        # Preserve full-oracle trace/state/output outcomes for escalation-without-duplication.
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
