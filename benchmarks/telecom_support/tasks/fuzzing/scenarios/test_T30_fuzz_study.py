"""Fuzzing study scenario for T30."""
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
TASK_ID = "T30"


def _scenario_facts(_store: TelcoStore) -> str:
    return (
        "- You moved house and need your address updated, then a replacement SIM.\n"
        "- Your new address is not verified yet; a SIM must not ship until that is sorted.\n"
    )

INTENT = "Handle address verification before replacement SIM order."
PERSONAS = [
    Persona(0, "cooperative_mover", "cooperative", "Provides new address details when asked.", "reveal_when_prompted", "low"),
    Persona(1, "impatient_delivery_focused_user", "impatient", "Pushes for immediate shipment.", "reveal_upfront", "medium"),
    Persona(2, "unclear_address_user", "uncertain", "Provides partial address first.", "reveal_when_prompted", "low"),
    Persona(3, "security_conscious_user", "cautious", "Asks why verification is required.", "reveal_when_prompted", "low"),
    Persona(4, "temporary_address_user", "boundary_testing", "Requests non-default delivery location.", "reveal_when_prompted", "medium"),
]
@ek.fixture
async def store_us_t30():
    store = seeded_store(TASK_ID)
    try:
        yield store
    finally:
        cleanup_store(store)
@ek.fixture
async def task_agent_us_t30(store_us_t30):
    yield wrap_reference_agent(store_us_t30)
@ek.fixture
@ek.parametrize("llm_model", llm_model_cases())
@ek.parametrize("persona", persona_cases(PERSONAS))
async def user_simulator_us_t30(store_us_t30, llm_model: str, persona: Persona):
    yield build_user_simulator(
        llm_model=llm_model,
        prompt=build_user_prompt(
            task_id=TASK_ID,
            intent=INTENT,
            persona=persona,
            meta=store_us_t30.seed_meta,
            scenario_facts=_scenario_facts(store_us_t30),
        ),
    )
@ek.fixture
@ek.parametrize("fuzz_trial", fuzz_trial_cases(TASK_ID))
async def fuzz_trial_t30(fuzz_trial: FuzzTrial):
    yield fuzz_trial

@ek.scenario(agent_fixture="task_agent_us_t30", repeats=1, tags=("telecom", "fuzz-study", "task:T30", "method:manual", "oracle:F"))
async def test_t30_manual_fuzz_study(s, store_us_t30):
    bind_scenario_context("test_t30_manual_fuzz_study", variant="reference")
    from tasks.manual.test_T30 import test_t30_full
    await test_t30_full(s, store_us_t30)
@ek.scenario(agent_fixture="task_agent_us_t30", user_fixture="user_simulator_us_t30", repeats=1, tags=("telecom", "fuzz-study", "task:T30", "method:sim", "oracle:F"))
async def test_t30_sim_fuzz_study(s, store_us_t30):  # noqa: ARG001
    bind_scenario_context("test_t30_sim_fuzz_study", variant="reference")
    (
        s.simulate_conversation(
            seed_actor="user",
            seed_input=SIM_CHAT_OPEN,
            max_turns=5,
            stop_condition=sim_stop(
                "Assistant discusses address verification or update requirement before shipping.",
                "Assistant does not claim a replacement SIM has already been ordered.",
            ),
            stop_on_actor="agent",
        )
        .assert_tool_calls(
            [m.tool_call("authenticate_customer")],
            ordered=True,
            allow_extras=True,
            actor="agent",
            turn="up_to_now",
        )
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN, actor="agent", turn="up_to_now")
        .assert_that(lambda: o.assert_no_sim_orders(store_us_t30))
        .assert_output(
            to.clarification_output(
                "Acknowledges address must be verified or updated before shipping a SIM",
                "Does not state that a replacement SIM order has already been placed",
            ),
            actor="agent",
            turn="up_to_now",
        )
        .simulate_conversation(
            max_turns=6,
            stop_condition=sim_stop(
                "Assistant confirms address must be verified or updated before shipping a replacement SIM.",
                "Assistant has not placed or confirmed a replacement SIM order.",
            ),
            stop_on_actor="agent",
        )
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN, actor="agent", turn="up_to_now")
        .assert_that(lambda: o.assert_no_sim_orders(store_us_t30))
    )
@ek.scenario(agent_fixture="task_agent_us_t30", repeats=1, tags=("telecom", "fuzz-study", "task:T30", "method:fuzz", "oracle:F"))
async def test_t30_fuzz_fuzz_study(s, store_us_t30, fuzz_trial_t30: FuzzTrial):
    bind_scenario_context("test_t30_fuzz_fuzz_study", variant="reference")
    cfg0 = fuzz_config_for_segment(task_id=TASK_ID, store=store_us_t30, fuzz_trial=fuzz_trial_t30, segment_index=0)
    cfg1 = fuzz_config_for_segment(task_id=TASK_ID, store=store_us_t30, fuzz_trial=fuzz_trial_t30, segment_index=1)
    (
        s.fuzz_conversation(
            fuzz_config=cfg0,
            trials=FUZZ_TRIALS,
            max_user_turns=max_turns_for_segment("T30", 0),
        )
        .assert_tool_calls(
            [m.tool_call("authenticate_customer")],
            ordered=True,
            allow_extras=True,
            actor="agent",
            turn="up_to_now",
        )
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN, actor="agent", turn="up_to_now")
        .assert_that(lambda: o.assert_no_sim_orders(store_us_t30))
        .assert_output(
            to.clarification_output(
                "Acknowledges address must be verified or updated before shipping a SIM",
                "Does not state that a replacement SIM order has already been placed",
            ),
            actor="agent",
            turn="up_to_now",
        )
        .fuzz_conversation(
            fuzz_config=cfg1,
            trials=FUZZ_TRIALS,
            max_user_turns=max_turns_for_segment("T30", 1),
        )
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN, actor="agent", turn="up_to_now")
        .assert_that(lambda: o.assert_no_sim_orders(store_us_t30))
    )
