"""Registered fault agent variant ids (F01–F15 scaffold + legacy pilots)."""

from __future__ import annotations

# Legacy pilot faults (implemented)
_LEGACY_FAULTS: tuple[str, ...] = (
    "fault_missing_ticket",
    "fault_skip_auth",
    "fault_premature_escalate",
    "fault_unsupported_credit",
    "fault_wrong_line",
    "fault_hallucinated_booking",
    "fault_wrong_nested_tool",
)

# F01–F15 scaffold (prompt/tool wiring expands with full task catalog)
_FAULT_F01_F15: tuple[str, ...] = (
    "fault_output_hallucination",  # F01
    "fault_missing_state_mutation",  # F02
    # fault_wrong_line — F03 (legacy)
    # fault_premature_escalate — F04 (legacy)
    # fault_unsupported_credit — F05 (legacy)
    "fault_auth_bypass",  # F06
    "fault_outage_order",  # F07
    "fault_duplicate_ticket",  # F08
    # fault_wrong_nested_tool — F09 (legacy)
    # F10 conditional structured output — task oracles
    # F11 LLM rubric — task oracles
    "fault_audit_omission",  # F12
    "fault_mixed_intent",  # F13
    "fault_stale_belief",  # F14
    "fault_privacy_leak",  # F15
)

FAULT_VARIANTS: tuple[str, ...] = tuple(
    dict.fromkeys(_LEGACY_FAULTS + _FAULT_F01_F15)
)

ALL_VARIANTS: tuple[str, ...] = ("reference",) + FAULT_VARIANTS
