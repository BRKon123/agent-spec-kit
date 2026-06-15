"""Extraction config for user-simulation extraction study (separate output dir)."""

from __future__ import annotations

import agent_spec_kit as ek

EXTRACT_CFG = ek.ExtractionConfig(
    target_file="../../regressions/extracted_sim/all_regressions.py",
    add_tags=("telecom", "regression", "user-sim", "extracted-sim"),
)
