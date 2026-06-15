"""Fuzzing study scenario for T43."""
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
TASK_ID = "T43"
INTENT = "Resolve issue on corrected line, not initially provided one."
PERSONAS = [
    Persona(0, "simple_correction", "cooperative", "States wrong line first; corrects to the right line quickly.", "reveal_upfront", "low"),
    Persona(1, "family_account_confusion", "uncertain", "Confuses family lines.", "reveal_when_prompted", "low"),
    Persona(2, "work_personal_mix_up", "uncertain", "Mixes work and personal line labels.", "reveal_when_prompted", "low"),
    Persona(3, "late_correction_after_tool_progress", "correcting", "Corrects after checks start.", "reveal_when_prompted", "medium"),
    Persona(4, "uncertain_user", "uncertain", "Starts unsure then becomes certain.", "reveal_when_prompted", "low"),
]


def _scenario_facts(store: TelcoStore) -> str:
    meta = store.seed_meta
    stale = str(meta.get("line_id_2", "LINE-WRONG"))
    return (
        "- Your SIM will not connect.\n"
        f"- You believe the affected line is {stale}.\n"
        f"- Your correct line for this issue is {meta['line_id']}.\n"
    )


@ek.fixture
async def store_us_t43():
    store = seeded_store(TASK_ID)
    try:
        yield store
    finally:
        cleanup_store(store)
@ek.fixture
async def task_agent_us_t43(store_us_t43):
    yield wrap_reference_agent(store_us_t43)
@ek.fixture
@ek.parametrize("llm_model", llm_model_cases())
@ek.parametrize("persona", persona_cases(PERSONAS))
async def user_simulator_us_t43(store_us_t43, llm_model: str, persona: Persona):
    yield build_user_simulator(
        llm_model=llm_model,
        prompt=build_user_prompt(
            task_id=TASK_ID,
            intent=INTENT,
            persona=persona,
            meta=store_us_t43.seed_meta,
            scenario_facts=_scenario_facts(store_us_t43),
        ),
    )
@ek.fixture
@ek.parametrize("fuzz_trial", fuzz_trial_cases(TASK_ID))
async def fuzz_trial_t43(fuzz_trial: FuzzTrial):
    yield fuzz_trial

@ek.scenario(
    agent_fixture="task_agent_us_t43",
    repeats=1,
    tags=("telecom", "fuzz-study", "task:T43", "method:manual", "oracle:F"),
)
async def test_t43_manual_fuzz_study(s, store_us_t43):
    bind_scenario_context("test_t43_manual_fuzz_study", variant="reference")
    from tasks.manual.test_T43 import test_t43_full
    await test_t43_full(s, store_us_t43)
@ek.scenario(
    agent_fixture="task_agent_us_t43",
    user_fixture="user_simulator_us_t43",
    repeats=1,
    tags=("telecom", "fuzz-study", "task:T43", "method:sim", "oracle:F"),
)
async def test_t43_sim_fuzz_study(s, store_us_t43):  # noqa: ARG001
    bind_scenario_context("test_t43_sim_fuzz_study", variant="reference")
    stale = o.stale_line_id(store_us_t43)
    (
        s.simulate_conversation(
            seed_actor="user",
            seed_input=SIM_CHAT_OPEN,
            max_turns=5,
            stop_condition=sim_stop(
                "Assistant asks for the correct line or acknowledges previous line may be wrong",
                "Assistant does not claim a final resolution yet",
            ),
            stop_on_actor="agent",
        )
        .forbid_tool_calls(to.PREMATURE_TICKET, actor="agent", turn="up_to_now")
        .assert_that(lambda: o.assert_no_ticket_on_line(store_us_t43, stale))
        .simulate_conversation(
            max_turns=5,
            stop_condition=sim_stop(
                "Assistant acknowledges user corrected which line should be used.",
                "Assistant avoids saying ticket already opened on stale/wrong line.",
            ),
            stop_on_actor="agent",
        )
        .forbid_tool_calls(to.PREMATURE_TICKET, actor="agent", turn="up_to_now")
        .assert_output(
            to.clarification_output(
                "Acknowledges the customer corrected which line needs the ticket",
                "Does not confirm a ticket was opened on the wrong line before correction",
            ),
            actor="agent",
            turn="up_to_now",
        )
        .simulate_conversation(
            max_turns=7,
            stop_condition=sim_stop(
                "Assistant opened a ticket or gave a clear resolution path on the corrected customer line.",
                "Assistant did not treat the wrong/stale line as fully resolved.",
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
        .assert_that(lambda: o.assert_no_ticket_on_line(store_us_t43, stale))
        .assert_that(
            lambda: o.assert_latest_ticket_reason_excludes(
                store_us_t43,
                "billing",
                "invoice",
                "plan dispute",
            )
        )
        .assert_output(
            to.issue_binding_output(
                "Confirms a support ticket on the customer's main line for SIM or connectivity",
                "Does not describe the issue only as a billing or plan dispute",
            ),
            actor="agent",
            turn="up_to_now",
        )
    )
@ek.scenario(
    agent_fixture="task_agent_us_t43",
    repeats=1,
    tags=("telecom", "fuzz-study", "task:T43", "method:fuzz", "oracle:F"),
)
async def test_t43_fuzz_fuzz_study(s, store_us_t43, fuzz_trial_t43: FuzzTrial):
    bind_scenario_context("test_t43_fuzz_fuzz_study", variant="reference")
    stale = o.stale_line_id(store_us_t43)
    cfg0 = fuzz_config_for_segment(task_id=TASK_ID, store=store_us_t43, fuzz_trial=fuzz_trial_t43, segment_index=0)
    cfg1 = fuzz_config_for_segment(task_id=TASK_ID, store=store_us_t43, fuzz_trial=fuzz_trial_t43, segment_index=1)
    cfg2 = fuzz_config_for_segment(task_id=TASK_ID, store=store_us_t43, fuzz_trial=fuzz_trial_t43, segment_index=2)
    (
        s.fuzz_conversation(
            fuzz_config=cfg0,
            trials=FUZZ_TRIALS,
            max_user_turns=max_turns_for_segment("T43", 0),
        )
        .forbid_tool_calls(to.PREMATURE_TICKET, actor="agent", turn="up_to_now")
        .assert_that(lambda: o.assert_no_ticket_on_line(store_us_t43, stale))
        .fuzz_conversation(
            fuzz_config=cfg1,
            trials=FUZZ_TRIALS,
            max_user_turns=max_turns_for_segment("T43", 1),
        )
        .forbid_tool_calls(to.PREMATURE_TICKET, actor="agent", turn="up_to_now")
        .assert_output(
            to.clarification_output(
                "Acknowledges the customer corrected which line needs the ticket",
                "Does not confirm a ticket was opened on the wrong line before correction",
            ),
            actor="agent",
            turn="up_to_now",
        )
        .fuzz_conversation(
            fuzz_config=cfg2,
            trials=FUZZ_TRIALS,
            max_user_turns=max_turns_for_segment("T43", 2),
        )
        .assert_tool_calls(
            [m.tool_call("authenticate_customer")],
            ordered=True,
            allow_extras=True,
            actor="agent",
            turn="up_to_now",
        )
        .assert_that(lambda: o.assert_no_ticket_on_line(store_us_t43, stale))
        .assert_that(
            lambda: o.assert_latest_ticket_reason_excludes(
                store_us_t43,
                "billing",
                "invoice",
                "plan dispute",
            )
        )
        .assert_output(
            to.issue_binding_output(
                "Confirms a support ticket on the customer's main line for SIM or connectivity",
                "Does not describe the issue only as a billing or plan dispute",
            ),
            actor="agent",
            turn="up_to_now",
        )
    )
