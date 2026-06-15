"""Shared shrink/extraction config for user-simulation study scenarios."""

from __future__ import annotations

import agent_spec_kit as ek

SHRINK_CFG = ek.ShrinkConfig(
    passes=(
        ek.shrink.remove_user_turns(),
        ek.shrink.simplify_user_messages(),
    ),
    confirm_runs=2,
)

EXTRACT_CFG = ek.ExtractionConfig(
    target_file="../../regressions/extracted_sim_regressions.py",
    add_tags=("telecom", "regression", "user-sim"),
)
