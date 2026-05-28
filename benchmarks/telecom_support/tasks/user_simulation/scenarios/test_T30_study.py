"""User simulation study scenario for T30."""
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
TASK_ID = "T30"
INTENT = "Handle address verification before replacement SIM order."
PERSONAS = [
    Persona(0, "cooperative_mover", "cooperative", "Provides new address details when asked.", "clarifies_after_prompt", "low"),
    Persona(1, "impatient_delivery_focused_user", "impatient", "Pushes for immediate shipment.", "early_full", "medium"),
    Persona(2, "unclear_address_user", "uncertain", "Provides partial address first.", "progressive", "low"),
    Persona(3, "security_conscious_user", "cautious", "Asks why verification is required.", "clarifies_after_prompt", "low"),
    Persona(4, "temporary_address_user", "boundary_testing", "Requests non-default delivery location.", "progressive", "medium"),
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
    yield build_user_simulator(llm_model=llm_model, prompt=build_user_prompt(task_id=TASK_ID, intent=INTENT, persona=persona, meta=store_us_t30.seed_meta))
@ek.scenario(agent_fixture="task_agent_us_t30", repeats=1, tags=("telecom", "user-simulation", "task:T30", "method:manual", "oracle:F"))
async def test_t30_manual_study(s, store_us_t30):
    bind_scenario_context("test_t30_manual_study", variant="reference")
    from tasks.manual.test_T30 import test_t30_full
    await test_t30_full(s, store_us_t30)
@ek.scenario(agent_fixture="task_agent_us_t30", user_fixture="user_simulator_us_t30", repeats=1, tags=("telecom", "user-simulation", "task:T30", "method:sim", "oracle:F"))
async def test_t30_sim_study(s, store_us_t30):  # noqa: ARG001
    bind_scenario_context("test_t30_sim_study", variant="reference")
    (
        # manual_checkpoint_1 -> sim_segment_1:
        # Match manual expectation that auth/clarification happens before any SIM order.
        s.simulate_conversation(
            seed_actor="user",
            seed_input="Session start. Explain your support request.",
            max_turns=4,
            stop_condition=m.llm_criteria(
                criteria=[
                    "Assistant discusses address verification or update requirement before shipping.",
                    "Assistant does not claim a replacement SIM has already been ordered.",
                ],
                threshold=1,
                model="openai:gpt-5-nano",
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
        # manual_checkpoint_2 -> sim_segment_2:
        # Continue while preserving full oracle no-order constraint across cumulative trace.
        .simulate_conversation(max_turns=6)
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN, actor="agent", turn="up_to_now")
        .assert_that(lambda: o.assert_no_sim_orders(store_us_t30))
    )
