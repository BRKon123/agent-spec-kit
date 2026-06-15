"""Fault-seeded agent variants (prompt or tool-wrapper faults)."""

from agents.faults.registry import (
    FAULT_DETECTION_VARIANTS,
    FAULT_FAMILY_VARIANTS,
    FAULT_VARIANTS,
    LEGACY_FAULTS,
)

__all__ = [
    "FAULT_DETECTION_VARIANTS",
    "FAULT_FAMILY_VARIANTS",
    "FAULT_VARIANTS",
    "LEGACY_FAULTS",
]
