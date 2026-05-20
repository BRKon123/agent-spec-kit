"""Export normalized tool traces from scenario results."""

from __future__ import annotations

from typing import Any

from agent_spec_kit.scenario_core import tool_dicts_from_turn_data
from agent_spec_kit.run import ConversationTurn, TurnResult

from shared.trace_io import save_trace


def export_from_turn_result(tr: TurnResult) -> dict[str, Any]:
    ct = ConversationTurn.from_turn("agent", tr)
    return {
        "output": tr.output,
        "tools": tool_dicts_from_turn_data(ct),
    }


def export_and_save(check_id: str, tr: TurnResult) -> None:
    save_trace(check_id, export_from_turn_result(tr))
