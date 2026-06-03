"""Offline scenarios for compare-page screenshots (baseline / v1 / v3).

Run from repo root::

    ASK_COMPARE_VARIANT=baseline uv run agent-spec-kit run examples/compare_screenshot_demo/ --experiment baseline
    ASK_COMPARE_VARIANT=v1        uv run agent-spec-kit run examples/compare_screenshot_demo/ --experiment v1
    ASK_COMPARE_VARIANT=v3        uv run agent-spec-kit run examples/compare_screenshot_demo/ --experiment v3

Then open the UI and compare::

    uv run agent-spec-kit ui --open
    # http://127.0.0.1:8765/compare?experiments=baseline,v1,v3
"""

from __future__ import annotations

import agent_spec_kit as ek
import agent_spec_kit.match as m


@ek.scenario(
    agent_fixture="support_agent",
    repeats=1,
    tags=("compare-demo", "support", "pass-all"),
    timeout_s=10.0,
)
async def test_greeting_includes_welcome(s):
    s.user_message("Please greet the customer.")
    s.assert_output(m.contains("Welcome"))


@ek.scenario(
    agent_fixture="support_agent",
    repeats=1,
    tags=("compare-demo", "support", "pass-all"),
    timeout_s=10.0,
)
async def test_order_status_confirmed(s):
    s.user_message("What is the order status for my recent purchase?")
    s.assert_output(m.contains("confirmed"))


@ek.scenario(
    agent_fixture="support_agent",
    repeats=1,
    tags=("compare-demo", "support", "pass-all"),
    timeout_s=10.0,
)
async def test_shipping_standard_window(s):
    s.user_message("How long is standard shipping to London?")
    s.assert_output(m.contains("business days"))


@ek.scenario(
    agent_fixture="support_agent",
    repeats=1,
    tags=("compare-demo", "support", "diff-v3"),
    timeout_s=10.0,
)
async def test_refund_policy_thirty_days(s):
    s.user_message("What is your refund policy?")
    s.assert_output(m.contains("30 days"))


@ek.scenario(
    agent_fixture="support_agent",
    repeats=1,
    tags=("compare-demo", "support", "diff-v1"),
    timeout_s=10.0,
)
async def test_cart_total_tool_result(s):
    s.user_message("Add up the line items and tell me the cart total.")
    s.assert_tool_calls(
        [m.tool_call("add_line_items", result=m.number(min=44.0, max=45.0))],
        ordered=True,
        allow_extras=False,
    )


@ek.scenario(
    agent_fixture="support_agent",
    repeats=1,
    tags=("compare-demo", "support", "diff-v3"),
    timeout_s=10.0,
)
async def test_account_requires_sign_in(s):
    s.user_message("Can you access my account details?")
    s.assert_output(m.contains("sign in"))


@ek.scenario(
    agent_fixture="support_agent",
    repeats=1,
    tags=("compare-demo", "support", "diff-v3-only"),
    timeout_s=10.0,
)
async def test_shipping_is_standard_not_express(s):
    s.user_message("Give me the shipping estimate for London.")
    s.assert_output(m.contains("Standard shipping"))
