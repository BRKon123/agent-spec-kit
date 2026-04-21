"""Compatibility shim; prefer :mod:`agent_spec_kit.scenario_core`."""

from __future__ import annotations

from agent_spec_kit.scenario_core import Scenario, create_scenario

__all__ = ["Scenario", "create_scenario"]
