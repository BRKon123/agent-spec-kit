"""Scenario run context helpers (trace logging, no task-specific agent hints)."""

from __future__ import annotations

import os


def bind_scenario_context(scenario_id: str, *, variant: str = "reference") -> None:
    """Set env vars read by agent_wrap for JSONL trace logging."""
    os.environ["TELCO_SCENARIO_ID"] = scenario_id
    os.environ["TELCO_AGENT_VARIANT"] = variant
