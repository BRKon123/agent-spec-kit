"""Live-demo scenarios — Part I of the talk, shown on screen.

Maps to the SPEAKER_PLAN demo outline:

  DEMO STEP 1  (Author a scenario, it passes) ........ test_billing_credit
  DEMO STEP 2  (Make it fail precisely) .............. test_line_status_strict

Run (offline rehearsal or live with a key):

    uv run agent-spec-kit run demo/ --tags demo-pass   --experiment demo
    uv run agent-spec-kit run demo/ --tags demo-fail   --experiment demo

Then open the web UI for DEMO STEP 3:

    uv run agent-spec-kit ui --open
"""

from __future__ import annotations

import agent_spec_kit as ek
import agent_spec_kit.match as m


# --------------------------------------------------------------------------- #
# DEMO STEP 1 — author a scenario, run it, watch it pass (~2 min)
#
# Talk through it top to bottom: it reads like the conversation, with the
# contract (Output / Trace / State) woven in after the turn.
# --------------------------------------------------------------------------- #


def credit_applied(store) -> None:
    """State oracle: billing was read, and only after authentication."""
    assert store.authenticated, "agent must authenticate before touching billing"
    assert store.billing_reads >= 1, "agent never read the billing record"
    assert not store.pre_auth_disclosures, (
        f"account id disclosed before auth: {store.pre_auth_disclosures}"
    )


@ek.scenario(
    agent_fixture="support_agent",
    tags=("demo", "demo-pass"),
    timeout_s=90.0,
)
async def test_billing_credit(s, store):
    # The customer authenticates up front, then asks about the double charge.
    s.user_message(
        "Hi, I'm CUST-045 and my verification token is TKN-9. "
        "I was double charged in October — can you check my billing?"
    )

    # O: the reply should speak to the billing outcome (robust to phrasing).
    s.assert_output(
        m.one_of(
            m.contains("charge"),
            m.contains("invoice"),
            m.contains("bill"),
            m.contains("credit"),
            m.contains("refund"),
        )
    )

    # T: authenticate BEFORE the account tool, in that order.
    s.assert_tool_calls(
        [
            m.tool_call("authenticate_customer"),
            m.tool_call("get_billing", args={"customer_id": "CUST-045"}),
        ],
        ordered=True,
        allow_extras=True,
    )

    # S: the store ended in the right shape (the function is injected by name).
    s.assert_that(credit_applied)


# --------------------------------------------------------------------------- #
# DEMO STEP 2 — make it fail precisely (~2 min)
#
# This is the "tighten one assertion" scenario. The customer asks about
# LINE-002, but the oracle below expects LINE-001 — so the trace assertion
# fails with a counterexample pointing at the exact path:
#
#     path  $[1].args.line_id
#     expected  LINE-001
#     actual    LINE-002
#
# (Exactly the counterexample on the "Precise diagnostics" slide.)
#
# To show the "live tightening", run test_billing_credit first, then run this
# one — or edit the line_id below from LINE-001 to LINE-002 to make it pass.
# --------------------------------------------------------------------------- #


@ek.scenario(
    agent_fixture="support_agent",
    tags=("demo", "demo-fail"),
    timeout_s=90.0,
)
async def test_line_status_strict(s, store):
    s.user_message(
        "I'm CUST-045, token TKN-9. Please check the status of my line LINE-002."
    )

    s.assert_tool_calls(
        [
            m.tool_call("authenticate_customer"),
            # Intentionally wrong: the customer asked about LINE-002.
            m.tool_call("get_line_status", args={"line_id": "LINE-001"}),
        ],
        ordered=True,
        allow_extras=True,
    )
