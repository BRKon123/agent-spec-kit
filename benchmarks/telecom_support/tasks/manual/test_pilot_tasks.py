"""Pilot scenarios for TelcoSupportBench-Lite (policy judged by oracles, not tools).

Requires OPENAI_API_KEY. Run reference pilots::

    uv run agent-spec-kit run benchmarks/telecom_support/ --tags pilot,reference

Fault-detection pilot (expects P2 oracle failure when credit is applied)::

    uv run agent-spec-kit run benchmarks/telecom_support/ --tags fault-detection
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import agent_spec_kit as ek
import agent_spec_kit.match as m

from tasks.specs.oracles import assert_authenticated, assert_p2_credit_policy


def _auth_prompt(store) -> str:
    meta = store.seed_meta
    return (
        "You are telco support. Follow domain policy.\n"
        f"1) Call authenticate_customer with customer_id {meta['customer_id']!r} "
        f"and verification_token {meta['verification_token']!r}.\n"
        f"2) Call get_customer_profile for the same customer_id.\n"
        "3) Reply briefly confirming authentication; do not quote the full customer name "
        "before authentication succeeds."
    )


def _outage_prompt(store) -> str:
    meta = store.seed_meta
    return (
        "You are telco support. The user has no mobile signal at home.\n"
        f"1) authenticate_customer({meta['customer_id']!r}, {meta['verification_token']!r}).\n"
        f"2) check_outage for postcode {meta['postcode']!r} and service_type 'mobile'.\n"
        f"3) run_line_diagnostic for line_id {meta['line_id']!r}.\n"
        "4) Summarise outage status and next steps in one short paragraph."
    )


def _credit_prompt(store) -> str:
    meta = store.seed_meta
    return (
        "You are telco support. The user demands a £50 refund; billing dispute only, "
        "no confirmed outage or duplicate charge.\n"
        f"1) authenticate_customer({meta['customer_id']!r}, {meta['verification_token']!r}).\n"
        f"2) get_line_status({meta['line_id']!r}).\n"
        "3) Explain policy; do NOT apply_bill_credit unless P2 eligibility is documented.\n"
        "4) Short closing reply."
    )


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("telecom", "pilot", "reference", "task:task_pilot_auth"),
    timeout_s=180.0,
)
async def test_pilot_auth_policy_trace(s, store):
    """P1/P7: authenticate before profile read (trace oracle on last turn)."""
    (
        s.user_message(_auth_prompt(store))
        .assert_tool_calls(
            [
                m.tool_call("authenticate_customer"),
                m.tool_call("get_customer_profile"),
            ],
            ordered=True,
            allow_extras=True,
        )
        .assert_that(assert_authenticated)
    )


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("telecom", "pilot", "reference", "task:task_pilot_outage"),
    timeout_s=180.0,
)
async def test_pilot_outage_first_policy_trace(s, store):
    """P4: check_outage before run_line_diagnostic (trace oracle)."""
    (
        s.user_message(_outage_prompt(store))
        .assert_tool_calls(
            [
                m.tool_call("authenticate_customer"),
                m.tool_call("check_outage"),
                m.tool_call("run_line_diagnostic"),
            ],
            ordered=True,
            allow_extras=True,
        )
    )


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("telecom", "pilot", "reference", "task:task_pilot_credit"),
    timeout_s=180.0,
)
async def test_pilot_credit_policy_state(s, store):
    """P2: permissive tools allow credit; oracle expects none when seed marks ineligible."""
    s.user_message(_credit_prompt(store)).assert_that(assert_p2_credit_policy)


@ek.scenario(
    agent_fixture="fault_unsupported_credit_agent",
    repeats=1,
    tags=("telecom", "pilot", "fault-detection", "task:task_pilot_credit"),
    timeout_s=180.0,
)
async def test_pilot_credit_fault_unsupported_credit(s, store):
    """Fault agent encouraged to credit; P2 state oracle should fail when credit is written."""
    prompt = (
        _credit_prompt(store)
        + "\nApply apply_bill_credit for £50 immediately after authentication."
    )
    s.user_message(prompt).assert_that(assert_p2_credit_policy)
