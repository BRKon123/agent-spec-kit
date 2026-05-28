"""User simulation study scenario for T43."""
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
from tasks.user_simulation.scenarios.common import (
    Persona,
    build_user_prompt,
    build_user_simulator,
    cleanup_store,
    llm_model_cases,
    persona_cases,
    seeded_store,
)
TASK_ID = "T43"
INTENT = "Resolve issue on corrected line, not initially provided one."
PERSONAS = [
    Persona(0, "simple_correction", "cooperative", "Corrects line quickly.", "early_correction", "low"),
    Persona(1, "family_account_confusion", "uncertain", "Confuses family lines.", "clarifies_after_prompt", "low"),
    Persona(2, "work_personal_mix_up", "uncertain", "Mixes work and personal line labels.", "progressive", "low"),
    Persona(3, "late_correction_after_tool_progress", "correcting", "Corrects after checks start.", "late_correction", "medium"),
    Persona(4, "uncertain_user", "uncertain", "Starts unsure then becomes certain.", "late_correction", "low"),
]
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
    yield build_user_simulator(llm_model=llm_model, prompt=build_user_prompt(task_id=TASK_ID, intent=INTENT, persona=persona, meta=store_us_t43.seed_meta))
@ek.scenario(
    agent_fixture="task_agent_us_t43",
    repeats=1,
    tags=("telecom", "user-simulation", "task:T43", "method:manual", "oracle:F"),
)
async def test_t43_manual_study(s, store_us_t43):
    bind_scenario_context("test_t43_manual_study", variant="reference")
    from tasks.manual.test_T43 import test_t43_full
    await test_t43_full(s, store_us_t43)
@ek.scenario(
    agent_fixture="task_agent_us_t43",
    user_fixture="user_simulator_us_t43",
    repeats=1,
    tags=("telecom", "user-simulation", "task:T43", "method:sim", "oracle:F"),
)
async def test_t43_sim_study(s, store_us_t43):  # noqa: ARG001
    bind_scenario_context("test_t43_sim_study", variant="reference")
    stale = o.stale_line_id(store_us_t43)
    (
        # manual_checkpoint_1 -> sim_segment_1:
        # Equivalent to pre-correction stage: no premature ticket on possibly wrong line.
        s.simulate_conversation(
            seed_actor="user",
            seed_input="Session start. Explain your support request.",
            max_turns=4,
            stop_condition=m.llm_criteria(
                criteria=[
                    "Assistant asks for the correct line or acknowledges previous line may be wrong",
                    "Assistant does not claim a final resolution yet",
                ],
                threshold=1,
                model="openai:gpt-5-nano",
            ),
            stop_on_actor="agent",
        )
        .forbid_tool_calls(to.PREMATURE_TICKET, actor="agent", turn="up_to_now")
        .assert_that(lambda: o.assert_no_ticket_on_line(store_us_t43, stale))
        # manual_checkpoint_2 -> sim_segment_2:
        # Equivalent to correction acknowledgement before final ticketing.
        .simulate_conversation(
            max_turns=4,
            stop_condition=m.llm_criteria(
                criteria=[
                    "Assistant acknowledges user corrected which line should be used.",
                    "Assistant avoids saying ticket already opened on stale/wrong line.",
                ],
                threshold=1,
                model="openai:gpt-5-nano",
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
        # manual_checkpoint_3 -> sim_segment_3:
        # End-of-run parity with manual trace/state/output.
        .simulate_conversation(max_turns=4)
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
