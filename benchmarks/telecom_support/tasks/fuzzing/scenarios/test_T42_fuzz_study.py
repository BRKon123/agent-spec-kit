"""Fuzzing study scenario for T42."""
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
TASK_ID = "T42"
INTENT = "Handle user issue change mid-conversation and update path."
PERSONAS = [
    Persona(0, "honest_correction_user", "honest", "Corrects mistaken details quickly when relevant.", "reveal_upfront", "low"),
    Persona(1, "confused_symptom_user", "confused", "Mixes symptom labels.", "reveal_when_prompted", "low"),
    Persona(2, "late_realisation_user", "realising", "Changes issue later in conversation.", "reveal_when_prompted", "medium"),
    Persona(3, "multi_issue_user", "multi_issue", "Mentions multiple issues before prioritizing.", "reveal_when_prompted", "medium"),
    Persona(4, "apologetic_corrector", "apologetic", "Explicitly apologizes while correcting.", "reveal_when_prompted", "low"),
]


def _scenario_facts(store: TelcoStore) -> str:
    meta = store.seed_meta
    return (
        "- Mobile data is not working at all.\n"
        f"- Your line is {meta['line_id']}.\n"
        "- You may have found your SIM in the laundry (you thought it was lost).\n"
        "- You do not want a replacement SIM shipped.\n"
        "- The core issue is still the data problem.\n"
    )


@ek.fixture
async def store_us_t42():
    store = seeded_store(TASK_ID)
    try:
        yield store
    finally:
        cleanup_store(store)
@ek.fixture
async def task_agent_us_t42(store_us_t42):
    yield wrap_reference_agent(store_us_t42)
@ek.fixture
@ek.parametrize("llm_model", llm_model_cases())
@ek.parametrize("persona", persona_cases(PERSONAS))
async def user_simulator_us_t42(store_us_t42, llm_model: str, persona: Persona):
    yield build_user_simulator(
        llm_model=llm_model,
        prompt=build_user_prompt(
            task_id=TASK_ID,
            intent=INTENT,
            persona=persona,
            meta=store_us_t42.seed_meta,
            scenario_facts=_scenario_facts(store_us_t42),
        ),
    )
@ek.fixture
@ek.parametrize("fuzz_trial", fuzz_trial_cases(TASK_ID))
async def fuzz_trial_t42(fuzz_trial: FuzzTrial):
    yield fuzz_trial

@ek.scenario(
    agent_fixture="task_agent_us_t42",
    repeats=1,
    tags=("telecom", "fuzz-study", "task:T42", "method:manual", "oracle:F"),
)
async def test_t42_manual_fuzz_study(s, store_us_t42):
    bind_scenario_context("test_t42_manual_fuzz_study", variant="reference")
    from tasks.manual.test_T42 import test_t42_full
    await test_t42_full(s, store_us_t42)
@ek.scenario(
    agent_fixture="task_agent_us_t42",
    user_fixture="user_simulator_us_t42",
    repeats=1,
    tags=("telecom", "fuzz-study", "task:T42", "method:sim", "oracle:F"),
)
async def test_t42_sim_fuzz_study(s, store_us_t42):  # noqa: ARG001
    bind_scenario_context("test_t42_sim_fuzz_study", variant="reference")
    (
        s.simulate_conversation(
            seed_actor="user",
            seed_input=SIM_CHAT_OPEN,
            max_turns=5,
            stop_condition=sim_stop(
                "Assistant asks clarifying questions about the issue or line status.",
                "Assistant does not confirm shipping or ordering a replacement SIM.",
            ),
            stop_on_actor="agent",
        )
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN, actor="agent", turn="up_to_now")
        .assert_output(
            to.clarification_output(
                "Does not confirm a replacement SIM order was placed before the customer clarified",
                "Addresses mobile data or line status rather than shipping a new SIM immediately",
            ),
            actor="agent",
            turn="up_to_now",
        )
        .simulate_conversation(
            max_turns=5,
            stop_condition=sim_stop(
                "Assistant acknowledges changed or corrected issue context from the user.",
                "Assistant still avoids confirming replacement SIM shipment.",
            ),
            stop_on_actor="agent",
        )
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN, actor="agent", turn="up_to_now")
        .assert_that(lambda: o.assert_no_mutations(store_us_t42))
        .assert_output(
            to.clarification_output(
                "Acknowledges the customer does not want a replacement SIM shipped",
                "Addresses the data issue or line status rather than ordering a new SIM",
            ),
            actor="agent",
            turn="up_to_now",
        )
        .simulate_conversation(
            max_turns=6,
            stop_condition=sim_stop(
                "Assistant focuses on mobile data connectivity or line status rather than ordering a SIM.",
                "Assistant does not confirm a replacement SIM was shipped or ordered.",
            ),
            stop_on_actor="agent",
        )
        .assert_that(lambda: o.assert_no_mutations(store_us_t42))
        .assert_output(
            to.issue_binding_output(
                "Focuses on mobile data connectivity or line status rather than ordering a replacement SIM",
                "Does not confirm a replacement SIM was shipped",
            ),
            actor="agent",
            turn="up_to_now",
        )
    )
@ek.scenario(
    agent_fixture="task_agent_us_t42",
    repeats=1,
    tags=("telecom", "fuzz-study", "task:T42", "method:fuzz", "oracle:F"),
)
async def test_t42_fuzz_fuzz_study(s, store_us_t42, fuzz_trial_t42: FuzzTrial):
    bind_scenario_context("test_t42_fuzz_fuzz_study", variant="reference")
    cfg0 = fuzz_config_for_segment(task_id=TASK_ID, store=store_us_t42, fuzz_trial=fuzz_trial_t42, segment_index=0)
    cfg1 = fuzz_config_for_segment(task_id=TASK_ID, store=store_us_t42, fuzz_trial=fuzz_trial_t42, segment_index=1)
    cfg2 = fuzz_config_for_segment(task_id=TASK_ID, store=store_us_t42, fuzz_trial=fuzz_trial_t42, segment_index=2)
    (
        s.fuzz_conversation(
            fuzz_config=cfg0,
            trials=FUZZ_TRIALS,
            max_user_turns=max_turns_for_segment("T42", 0),
        )
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN, actor="agent", turn="up_to_now")
        .assert_output(
            to.clarification_output(
                "Does not confirm a replacement SIM order was placed before the customer clarified",
                "Addresses mobile data or line status rather than shipping a new SIM immediately",
            ),
            actor="agent",
            turn="up_to_now",
        )
        .fuzz_conversation(
            fuzz_config=cfg1,
            trials=FUZZ_TRIALS,
            max_user_turns=max_turns_for_segment("T42", 1),
        )
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN, actor="agent", turn="up_to_now")
        .assert_that(lambda: o.assert_no_mutations(store_us_t42))
        .assert_output(
            to.clarification_output(
                "Acknowledges the customer does not want a replacement SIM shipped",
                "Addresses the data issue or line status rather than ordering a new SIM",
            ),
            actor="agent",
            turn="up_to_now",
        )
        .fuzz_conversation(
            fuzz_config=cfg2,
            trials=FUZZ_TRIALS,
            max_user_turns=max_turns_for_segment("T42", 2),
        )
        .assert_that(lambda: o.assert_no_mutations(store_us_t42))
        .assert_output(
            to.issue_binding_output(
                "Focuses on mobile data connectivity or line status rather than ordering a replacement SIM",
                "Does not confirm a replacement SIM was shipped",
            ),
            actor="agent",
            turn="up_to_now",
        )
    )
