"""Registered fault agent variants for mutation-style fault detection (F01–F06)."""

from __future__ import annotations

# F01–F06 primary families (used by fault_matrix.yaml and --tags fault-detection)
FAULT_F01_PREMATURE_ESCALATE = "fault_premature_escalate"
FAULT_F02_WRONG_LINE = "fault_wrong_line"
FAULT_F02_STALE_BELIEF = "fault_stale_belief"
FAULT_F03_UNSUPPORTED_CREDIT = "fault_unsupported_credit"
FAULT_F04_SKIP_AUTH = "fault_skip_auth"
FAULT_F04_PRIVACY_LEAK = "fault_privacy_leak"
FAULT_F05_WRONG_NESTED_TOOL = "fault_wrong_nested_tool"
FAULT_F06_STRUCTURED_OUTPUT = "fault_structured_output"

FAULT_FAMILY_VARIANTS: dict[str, tuple[str, ...]] = {
    "F01": (FAULT_F01_PREMATURE_ESCALATE,),
    "F02": (FAULT_F02_WRONG_LINE, FAULT_F02_STALE_BELIEF),
    "F03": (FAULT_F03_UNSUPPORTED_CREDIT,),
    "F04": (FAULT_F04_SKIP_AUTH, FAULT_F04_PRIVACY_LEAK),
    "F05": (FAULT_F05_WRONG_NESTED_TOOL,),
    "F06": (FAULT_F06_STRUCTURED_OUTPUT,),
}

FAULT_DETECTION_VARIANTS: tuple[str, ...] = tuple(
    dict.fromkeys(v for variants in FAULT_FAMILY_VARIANTS.values() for v in variants)
)

# Legacy / pilot variants (not in primary fault-detection matrix)
LEGACY_FAULTS: tuple[str, ...] = (
    "fault_missing_ticket",
    "fault_hallucinated_booking",
    "fault_output_hallucination",
    "fault_missing_state_mutation",
    "fault_auth_bypass",
    "fault_outage_order",
    "fault_duplicate_ticket",
    "fault_audit_omission",
    "fault_mixed_intent",
)

FAULT_VARIANTS: tuple[str, ...] = tuple(
    dict.fromkeys(FAULT_DETECTION_VARIANTS + LEGACY_FAULTS)
)

ALL_VARIANTS: tuple[str, ...] = ("reference",) + FAULT_VARIANTS
