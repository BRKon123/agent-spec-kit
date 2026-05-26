"""Registered fault agent variants for mutation-style fault detection (F01–F10)."""

from __future__ import annotations

# F01–F10 primary families (used by fault_matrix.yaml and --tags fault-detection)
FAULT_F01_PREMATURE_ESCALATE = "fault_premature_escalate"
FAULT_F02_WRONG_LINE = "fault_wrong_line"
FAULT_F02_STALE_BELIEF = "fault_stale_belief"
FAULT_F03_UNSUPPORTED_CREDIT = "fault_unsupported_credit"
FAULT_F04_SKIP_AUTH = "fault_skip_auth"
FAULT_F04_PRIVACY_LEAK = "fault_privacy_leak"
FAULT_F05_WRONG_NESTED_TOOL = "fault_wrong_nested_tool"
FAULT_F06_STRUCTURED_OUTPUT = "fault_structured_output"
FAULT_F07_MISSING_CLARIFICATION = "fault_missing_clarification"
FAULT_F08_AUDIT_OMISSION = "fault_audit_omission"
FAULT_F09_FAILURE_TO_ACT = "fault_failure_to_act"
FAULT_F10_WRONG_ISSUE_BINDING = "fault_wrong_issue_binding"

FAULT_FAMILY_VARIANTS: dict[str, tuple[str, ...]] = {
    "F01": (FAULT_F01_PREMATURE_ESCALATE,),
    "F02": (FAULT_F02_WRONG_LINE, FAULT_F02_STALE_BELIEF),
    "F03": (FAULT_F03_UNSUPPORTED_CREDIT,),
    "F04": (FAULT_F04_SKIP_AUTH, FAULT_F04_PRIVACY_LEAK),
    "F05": (FAULT_F05_WRONG_NESTED_TOOL,),
    "F06": (FAULT_F06_STRUCTURED_OUTPUT,),
    "F07": (FAULT_F07_MISSING_CLARIFICATION,),
    "F08": (FAULT_F08_AUDIT_OMISSION,),
    "F09": (FAULT_F09_FAILURE_TO_ACT,),
    "F10": (FAULT_F10_WRONG_ISSUE_BINDING,),
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
    "fault_mixed_intent",
)

FAULT_VARIANTS: tuple[str, ...] = tuple(
    dict.fromkeys(FAULT_DETECTION_VARIANTS + LEGACY_FAULTS)
)

ALL_VARIANTS: tuple[str, ...] = ("reference",) + FAULT_VARIANTS
