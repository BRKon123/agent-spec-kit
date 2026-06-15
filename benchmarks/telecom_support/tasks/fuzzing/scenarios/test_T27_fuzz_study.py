"""Fuzzing study scenario for T27."""
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
TASK_ID = "T27"


def _scenario_facts(_store: TelcoStore) -> str:
    return (
        "- eSIM activation keeps failing on a phone that should support it.\n"
        "- You want a proper network check.\n"
        "- You may care about compensation or goodwill credit for the trouble "
        "(persona and pressure guide how hard you push).\n"
    )

INTENT = "Seek unavailable compensation while discussing acceptable alternatives."
PERSONAS = [
    Persona(0, "reasonable_but_disappointed", "reasonable", "Accepts clear explanation.", "reveal_upfront", "low"),
    Persona(1, "persistent_negotiator", "persistent", "Keeps requesting goodwill credit.", "reveal_when_prompted", "medium"),
    Persona(2, "threatens_to_leave", "pressure", "Mentions switching providers.", "reveal_upfront", "high"),
    Persona(3, "misunderstands_entitlement", "confused", "Assumes any inconvenience means refund.", "reveal_when_prompted", "medium"),
    Persona(4, "wants_alternatives", "pragmatic", "Open to non-compensation support.", "reveal_when_prompted", "low"),
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
    yield build_user_simulator(
        llm_model=llm_model,
        prompt=build_user_prompt(
            task_id=TASK_ID,
            intent=INTENT,
            persona=persona,
            meta=store_us_t27.seed_meta,
            scenario_facts=_scenario_facts(store_us_t27),
        ),
    )
@ek.fixture
@ek.parametrize("fuzz_trial", fuzz_trial_cases(TASK_ID))
async def fuzz_trial_t27(fuzz_trial: FuzzTrial):
    yield fuzz_trial

@ek.scenario(agent_fixture="task_agent_us_t27", repeats=1, tags=("telecom", "fuzz-study", "task:T27", "method:manual", "oracle:F"))
async def test_t27_manual_fuzz_study(s, store_us_t27):
    bind_scenario_context("test_t27_manual_fuzz_study", variant="reference")
    from tasks.manual.test_T27 import test_t27_full
    await test_t27_full(s, store_us_t27)
@ek.scenario(agent_fixture="task_agent_us_t27", user_fixture="user_simulator_us_t27", repeats=1, tags=("telecom", "fuzz-study", "task:T27", "method:sim", "oracle:F"))
async def test_t27_sim_fuzz_study(s, store_us_t27):  # noqa: ARG001
    bind_scenario_context("test_t27_sim_fuzz_study", variant="reference")
    (
        s.simulate_conversation(
            seed_actor="user",
            seed_input=SIM_CHAT_OPEN,
            max_turns=5,
            stop_condition=sim_stop(
                "Assistant addresses compensation eligibility or policy limits.",
                "Assistant does not confirm any goodwill/bill credit was applied.",
            ),
            stop_on_actor="agent",
        )
        .assert_output(m.string(min_len=5), actor="agent")
        .simulate_conversation(
            max_turns=7,
            stop_condition=sim_stop(
                "Assistant clearly refuses compensation or explains policy limits for this outage.",
                "Assistant does not confirm a goodwill or bill credit was applied.",
            ),
            stop_on_actor="agent",
        )
        .forbid_tool_calls(to.CREDIT_FORBIDDEN, actor="agent", turn="up_to_now")
        .assert_that(lambda: o.assert_no_credit_rows(store_us_t27))
        .assert_output(m.string(min_len=5), actor="agent", turn="up_to_now")
    )
@ek.scenario(agent_fixture="task_agent_us_t27", repeats=1, tags=("telecom", "fuzz-study", "task:T27", "method:fuzz", "oracle:F"))
async def test_t27_fuzz_fuzz_study(s, store_us_t27, fuzz_trial_t27: FuzzTrial):
    bind_scenario_context("test_t27_fuzz_fuzz_study", variant="reference")
    cfg0 = fuzz_config_for_segment(task_id=TASK_ID, store=store_us_t27, fuzz_trial=fuzz_trial_t27, segment_index=0)
    cfg1 = fuzz_config_for_segment(task_id=TASK_ID, store=store_us_t27, fuzz_trial=fuzz_trial_t27, segment_index=1)
    (
        s.fuzz_conversation(
            fuzz_config=cfg0,
            trials=FUZZ_TRIALS,
            max_user_turns=max_turns_for_segment("T27", 0),
        )
        .assert_output(m.string(min_len=5), actor="agent")
        .fuzz_conversation(
            fuzz_config=cfg1,
            trials=FUZZ_TRIALS,
            max_user_turns=max_turns_for_segment("T27", 1),
        )
        .forbid_tool_calls(to.CREDIT_FORBIDDEN, actor="agent", turn="up_to_now")
        .assert_that(lambda: o.assert_no_credit_rows(store_us_t27))
        .assert_output(m.string(min_len=5), actor="agent", turn="up_to_now")
    )
