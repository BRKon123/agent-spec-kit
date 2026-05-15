"""Registered fault agent variant ids."""

from __future__ import annotations

FAULT_VARIANTS: tuple[str, ...] = (
    "fault_missing_ticket",
    "fault_skip_auth",
    "fault_premature_escalate",
    "fault_unsupported_credit",
    "fault_wrong_line",
    "fault_hallucinated_booking",
    "fault_wrong_nested_tool",
)

ALL_VARIANTS: tuple[str, ...] = ("reference",) + FAULT_VARIANTS
