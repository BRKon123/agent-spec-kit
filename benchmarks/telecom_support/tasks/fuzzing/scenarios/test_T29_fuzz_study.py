"""Fuzzing study scenario for T29."""
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
TASK_ID = "T29"


def _scenario_facts(store: TelcoStore) -> str:
    meta = store.seed_meta
    decoy = str(meta.get("decoy_line_id", "LINE-WRONG"))
    return (
        "- You need a replacement SIM.\n"
        f"- You believe the affected line is {decoy}.\n"
        f"- Your correct line is {meta['line_id']}.\n"
        "- You may want the SIM sent to your default address.\n"
    )

INTENT = "Resolve issue on the correct line after late clarification."
PERSONAS = [
    Persona(0, "cooperative_multi_line_user", "cooperative", "Confirms right line when asked.", "reveal_when_prompted", "low"),
    Persona(1, "ambiguous_my_phone_user", "ambiguous", "Says my phone without IDs.", "reveal_when_prompted", "medium"),
    Persona(2, "parent_account_holder", "uncertain", "Unsure which family line is affected.", "reveal_when_prompted", "low"),
    Persona(3, "business_style_user", "structured", "Uses work/personal labels.", "reveal_when_prompted", "low"),
    Persona(4, "late_correction_user", "correcting", "Corrects line after initial check starts.", "reveal_when_prompted", "medium"),
]
@ek.fixture
async def store_us_t29():
    store = seeded_store(TASK_ID)
    try:
        yield store
    finally:
        cleanup_store(store)
@ek.fixture
async def task_agent_us_t29(store_us_t29):
    yield wrap_reference_agent(store_us_t29)
@ek.fixture
@ek.parametrize("llm_model", llm_model_cases())
@ek.parametrize("persona", persona_cases(PERSONAS))
async def user_simulator_us_t29(store_us_t29, llm_model: str, persona: Persona):
    yield build_user_simulator(
        llm_model=llm_model,
        prompt=build_user_prompt(
            task_id=TASK_ID,
            intent=INTENT,
            persona=persona,
            meta=store_us_t29.seed_meta,
            scenario_facts=_scenario_facts(store_us_t29),
        ),
    )
@ek.fixture
@ek.parametrize("fuzz_trial", fuzz_trial_cases(TASK_ID))
async def fuzz_trial_t29(fuzz_trial: FuzzTrial):
    yield fuzz_trial

@ek.scenario(
    agent_fixture="task_agent_us_t29",
    repeats=1,
    tags=("telecom", "fuzz-study", "task:T29", "method:manual", "oracle:F"),
)
async def test_t29_manual_fuzz_study(s, store_us_t29):
    bind_scenario_context("test_t29_manual_fuzz_study", variant="reference")
    from tasks.manual.test_T29 import test_t29_full
    await test_t29_full(s, store_us_t29)
@ek.scenario(
    agent_fixture="task_agent_us_t29",
    user_fixture="user_simulator_us_t29",
    repeats=1,
    tags=("telecom", "fuzz-study", "task:T29", "method:sim", "oracle:F"),
)
async def test_t29_sim_fuzz_study(s, store_us_t29):  # noqa: ARG001
    bind_scenario_context("test_t29_sim_fuzz_study", variant="reference")
    decoy = to.decoy_line_id(store_us_t29)
    seed_line = str(store_us_t29.seed_meta["line_id"])
    (
        s.simulate_conversation(
            seed_actor="user",
            seed_input=SIM_CHAT_OPEN,
            max_turns=5,
            stop_condition=sim_stop(
                "Assistant asks for line clarification or identifies uncertainty about affected line",
                "Assistant does not claim the issue was already resolved",
            ),
            stop_on_actor="agent",
        )
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN, actor="agent", turn="up_to_now")
        .assert_that(lambda: o.assert_no_sim_order_on_line(store_us_t29, decoy))
        .assert_output(
            to.clarification_output(
                "Does not confirm a SIM order was placed on the wrong line",
                "Asks which line is correct or acknowledges line uncertainty",
            ),
            actor="agent",
            turn="up_to_now",
        )
        .simulate_conversation(
            max_turns=7,
            stop_condition=sim_stop(
                "Assistant confirms a replacement SIM order or clear next action on the corrected line.",
                "Assistant binds ordering context to the corrected customer line.",
            ),
            stop_on_actor="agent",
        )
        .assert_tool_calls(
            [
                m.tool_call("authenticate_customer"),
                to.order_sim_on_line(seed_line),
            ],
            ordered=True,
            allow_extras=True,
            actor="agent",
            turn="up_to_now",
        )
        .assert_that(lambda: o.assert_sim_orders_only_on_seed_line(store_us_t29))
        .assert_output(
            to.premature_action_output("LINE-WRONG", action="order"),
            actor="agent",
            turn="up_to_now",
        )
    )
@ek.scenario(
    agent_fixture="task_agent_us_t29",
    repeats=1,
    tags=("telecom", "fuzz-study", "task:T29", "method:fuzz", "oracle:F"),
)
async def test_t29_fuzz_fuzz_study(s, store_us_t29, fuzz_trial_t29: FuzzTrial):
    bind_scenario_context("test_t29_fuzz_fuzz_study", variant="reference")
    decoy = to.decoy_line_id(store_us_t29)
    seed_line = str(store_us_t29.seed_meta["line_id"])
    cfg0 = fuzz_config_for_segment(task_id=TASK_ID, store=store_us_t29, fuzz_trial=fuzz_trial_t29, segment_index=0)
    cfg1 = fuzz_config_for_segment(task_id=TASK_ID, store=store_us_t29, fuzz_trial=fuzz_trial_t29, segment_index=1)
    (
        s.fuzz_conversation(
            fuzz_config=cfg0,
            trials=FUZZ_TRIALS,
            max_user_turns=max_turns_for_segment("T29", 0),
        )
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN, actor="agent", turn="up_to_now")
        .assert_that(lambda: o.assert_no_sim_order_on_line(store_us_t29, decoy))
        .assert_output(
            to.clarification_output(
                "Does not confirm a SIM order was placed on the wrong line",
                "Asks which line is correct or acknowledges line uncertainty",
            ),
            actor="agent",
            turn="up_to_now",
        )
        .fuzz_conversation(
            fuzz_config=cfg1,
            trials=FUZZ_TRIALS,
            max_user_turns=max_turns_for_segment("T29", 1),
        )
        .assert_tool_calls(
            [
                m.tool_call("authenticate_customer"),
                to.order_sim_on_line(seed_line),
            ],
            ordered=True,
            allow_extras=True,
            actor="agent",
            turn="up_to_now",
        )
        .assert_that(lambda: o.assert_sim_orders_only_on_seed_line(store_us_t29))
        .assert_output(
            to.premature_action_output("LINE-WRONG", action="order"),
            actor="agent",
            turn="up_to_now",
        )
    )
