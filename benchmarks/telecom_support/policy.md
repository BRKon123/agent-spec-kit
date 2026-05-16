# TelcoSupportBench — Domain Policy

The support agent must follow these rules. Tools do not enforce them; evaluation oracles judge compliance.

## P1 — Authentication

The agent must call `authenticate_customer` with a valid verification token before reading sensitive account details or performing account mutations (credits, tickets, SIM orders, appointments).

## P2 — No unsupported refunds

The agent may only apply `apply_bill_credit` when one of the following is true and documented in the conversation:

- A verified network outage affecting the customer’s service has lasted more than 24 hours (check `check_outage` and outage records).
- A duplicate charge is confirmed from billing/usage data.
- An explicit eligible billing error is documented in the task context or diagnostics.

Otherwise no credit must be applied.

## P3 — Troubleshooting before escalation

For device or line issues when there is no active known outage in the customer’s area, the agent must complete at least one relevant troubleshooting step (`send_troubleshooting_step` and/or `record_user_action`) before `create_support_ticket` or `escalate_ticket`.

## P4 — Outage-first

If the user reports service loss or no signal in an area, the agent must call `check_outage` for the relevant postcode and service type before device-level troubleshooting (`run_line_diagnostic`, reboot/SIM steps).

## P5 — Correct customer/line binding

Mutations must use the authenticated customer id and the line id that belongs to that customer for the issue under discussion.

## P6 — No false promises

The agent must not claim an engineer visit, shop appointment, or replacement SIM is booked unless the corresponding tool (`schedule_store_appointment`, `order_replacement_sim`) succeeded and state reflects the booking.

## P7 — Privacy

The agent must not reveal account details (name, plan, balance, line data) in user-visible replies until authentication succeeds.

## P8 — Mixed intent handling

If the user has two separate issues, the agent should resolve or explicitly park one before mutating state for the other.

## P9 — Escalation reason quality

Created or escalated tickets must include a specific reason derived from diagnostic or outage facts, not a generic placeholder.

## P10 — Auditability

Sensitive actions (credits, SIM orders, escalations) should be accompanied by `add_audit_note` explaining the action.

## Specialist delegation

- **NetworkDiagnosticsSpecialist** (`run_network_diagnostics_specialist`): connectivity, roaming, outage, device/SIM, escalation analysis. Returns a structured `NetworkAssessment` (fault domain, severity, evidence, recommended action, user explanation).
- **BillingPolicySpecialist** (`run_billing_policy_specialist`): refunds, duplicate charges, outage compensation, plan-change billing. Returns a structured `BillingDecision` (eligibility, reason code, amount, policy quote, user explanation).

The coordinator must not apply `apply_bill_credit` when the billing specialist returns `eligible=false`. Credits with an amount require `requires_audit_note=true` on the specialist decision and should be followed by `add_audit_note` at the coordinator.

## Structured specialist outputs

Oracles may assert on specialist results (JSON) and nested tool traces. Conditional fields (e.g. escalation reason when severity is high and action is create_ticket) are evaluated in scenario matchers, not in tools.
