# Canonical oracle semantics (C01–C12)

All frameworks must enforce the same policy with check logic inlined inside `# CHECK_START` / `# CHECK_END` in each port file, written with **that framework’s native tools** (see [`NATIVE_PORT_POLICY.md`](NATIVE_PORT_POLICY.md)). [`shared/canonical_checks.py`](shared/canonical_checks.py) is the semantic oracle for golden-trace parity tests. `scripts/materialize_inline_checks.py` regenerates **pytest** only.

| ID | Policy (what every framework checks) |
|----|--------------------------------------|
| C01 | Final `output` mentions credit/refund **and** $/dollar (deterministic proxy). |
| C02 | `run_network_diagnostics_specialist.result` has **exactly** keys `severity`, `recommended_action`, `escalation_reason`; values `high`, `create_ticket`, non-empty reason. |
| C03 | `run_billing_policy_specialist.result`: if `eligible` then `amount` > 0; if not eligible then `amount` absent. |
| C04 | Billing result: `eligible is True` and `0.01 <= amount <= 500`. |
| C05 | Root tools contain subsequence `authenticate_customer` → `get_outage_status` (extras allowed). |
| C06 | Root tools must **not** include `apply_bill_credit`. |
| C07 | Subsequence `authenticate_customer` → `get_line_status`; `get_line_status.args.line_id == LINE-001`. |
| C08 | Specialist result keys exactly `severity`, `recommended_action`, `summary`; severity ∈ {medium, high}; action len ≥ 1; summary len ≥ 10. |
| C09 | Specialist `children` names exactly `pull_network_events`, `score_signal_anomaly` in order. |
| C10 | Root tools include both `heartbeat_ping` and `get_line_status` (any order, extras OK). |
| C11 | After simulating ticket insert on seeded store, `assert_ticket_exists`. |
| C12 | Last turn subsequence `authenticate_customer` → `create_support_ticket`; ticket exists for corrected `LINE-001`. |

**agent_spec_kit** expresses the same rules with matchers (`m.object`, `forbid_tool_calls`, …); see
[`tests/test_ask_matcher_parity.py`](tests/test_ask_matcher_parity.py).
