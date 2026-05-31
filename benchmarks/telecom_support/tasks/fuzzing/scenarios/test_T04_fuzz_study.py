"""Fuzzing study scenario for T04."""
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
TASK_ID = "T04"
INTENT = "Escalate data failure after restart was already attempted."
PERSONAS = [
    Persona(0, "straightforward_reporter", "cooperative", "States restart already done.", "reveal_upfront", "low"),
    Persona(1, "frustrated_but_cooperative", "frustrated", "Wants quick escalation but answers questions.", "reveal_upfront", "medium"),
    Persona(2, "evidence_heavy_user", "detailed", "Shares timestamps and observed symptoms.", "reveal_upfront", "low"),
    Persona(3, "minimal_answer_user", "brief", "Keeps replies short until the agent asks follow-ups.", "reveal_when_prompted", "low"),
    Persona(4, "skeptical_user", "skeptical", "Questions why diagnostics are needed.", "reveal_when_prompted", "medium"),
]


def _scenario_facts(store: TelcoStore) -> str:
    meta = store.seed_meta
    return (
        f"- Mobile data is not working on line {meta['line_id']}.\n"
        "- Whether you have already restarted is up to your persona; you want help if it is still broken.\n"
    )


@ek.fixture
async def store_us_t04():
    store = seeded_store(TASK_ID)
    try:
        yield store
    finally:
        cleanup_store(store)


@ek.fixture
async def task_agent_us_t04(store_us_t04):
    yield wrap_reference_agent(store_us_t04)


@ek.fixture
@ek.parametrize("llm_model", llm_model_cases())
@ek.parametrize("persona", persona_cases(PERSONAS))
async def user_simulator_us_t04(store_us_t04, llm_model: str, persona: Persona):
    prompt = build_user_prompt(
        task_id=TASK_ID,
        intent=INTENT,
        persona=persona,
        meta=store_us_t04.seed_meta,
        scenario_facts=_scenario_facts(store_us_t04),
    )
    yield build_user_simulator(llm_model=llm_model, prompt=prompt)


@ek.fixture
@ek.parametrize("fuzz_trial", fuzz_trial_cases(TASK_ID))
async def fuzz_trial_t04(fuzz_trial: FuzzTrial):
    yield fuzz_trial

@ek.scenario(agent_fixture="task_agent_us_t04", repeats=1, tags=("telecom", "fuzz-study", "task:T04", "method:manual", "oracle:F"))
async def test_t04_manual_fuzz_study(s, store_us_t04):
    bind_scenario_context("test_t04_manual_fuzz_study", variant="reference")
    from tasks.manual.test_T04 import test_t04_full
    await test_t04_full(s, store_us_t04)


@ek.scenario(agent_fixture="task_agent_us_t04", user_fixture="user_simulator_us_t04", repeats=1, tags=("telecom", "fuzz-study", "task:T04", "method:sim", "oracle:F"))
async def test_t04_sim_fuzz_study(s, store_us_t04):  # noqa: ARG001
    bind_scenario_context("test_t04_sim_fuzz_study", variant="reference")
    (
        s.simulate_conversation(
            seed_actor="user",
            seed_input=SIM_CHAT_OPEN,
            max_turns=5,
            stop_condition=sim_stop(
                "Assistant acknowledges restart or asks to confirm restart/diagnostic context.",
                "Assistant has not yet clearly confirmed that a support ticket was created.",
            ),
            stop_on_actor="agent",
        )
        .assert_output(m.string(min_len=5), actor="agent")
        .simulate_conversation(
            max_turns=7,
            stop_condition=sim_stop(
                "Assistant confirms a support ticket was created or clearly commits to opening one.",
                "The connectivity issue has been addressed with a concrete next step.",
            ),
            stop_on_actor="agent",
        )
        .assert_tool_calls(
            [
                m.tool_call("record_user_action"),
                m.tool_call("create_support_ticket"),
            ],
            ordered=True,
            allow_extras=True,
            actor="agent",
            turn="up_to_now",
        )
        .assert_that(lambda: o.assert_ticket_exists(store_us_t04))
        .assert_output(
            to.mutation_claim_output("Confirms a support ticket was opened"),
            actor="agent",
            turn="up_to_now",
        )
    )


@ek.scenario(agent_fixture="task_agent_us_t04", repeats=1, tags=("telecom", "fuzz-study", "task:T04", "method:fuzz", "oracle:F"))
async def test_t04_fuzz_fuzz_study(s, store_us_t04, fuzz_trial_t04: FuzzTrial):
    bind_scenario_context("test_t04_fuzz_fuzz_study", variant="reference")
    cfg0 = fuzz_config_for_segment(task_id=TASK_ID, store=store_us_t04, fuzz_trial=fuzz_trial_t04, segment_index=0)
    cfg1 = fuzz_config_for_segment(task_id=TASK_ID, store=store_us_t04, fuzz_trial=fuzz_trial_t04, segment_index=1)
    (
        s.fuzz_conversation(
            fuzz_config=cfg0,
            trials=FUZZ_TRIALS,
            max_user_turns=max_turns_for_segment("T04", 0),
        )
        .assert_output(m.string(min_len=5), actor="agent")
        .fuzz_conversation(
            fuzz_config=cfg1,
            trials=FUZZ_TRIALS,
            max_user_turns=max_turns_for_segment("T04", 1),
        )
        .assert_tool_calls(
            [
                m.tool_call("record_user_action"),
                m.tool_call("create_support_ticket"),
            ],
            ordered=True,
            allow_extras=True,
            actor="agent",
            turn="up_to_now",
        )
        .assert_that(lambda: o.assert_ticket_exists(store_us_t04))
        .assert_output(
            to.mutation_claim_output("Confirms a support ticket was opened"),
            actor="agent",
            turn="up_to_now",
        )
    )
