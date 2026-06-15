"""Scripted AdaptedAgent that replays frozen traces (no live LLM)."""

from __future__ import annotations

from typing import Any

from agent_spec_kit.run import AdaptedAgent, TurnResult

from shared.trace_io import load_trace, turn_result_from_trace, turn_results_from_multitrace


class ScriptedTraceAgent:
    """Replay one or more turns from a frozen trace JSON file."""

    def __init__(self, check_id: str) -> None:
        self._trace = load_trace(check_id)
        self._multi = "turns" in self._trace
        if self._multi:
            self._turns = turn_results_from_multitrace(self._trace)
            self._i = 0
        else:
            self._turns = None
            self._i = 0

    async def run_turn(self, user_message: str) -> TurnResult:
        if self._multi and self._turns is not None:
            if self._i >= len(self._turns):
                return TurnResult(
                    output="(exhausted)",
                    events=(),
                    status="error",
                    error="scripted turns exhausted",
                )
            tr = self._turns[self._i]
            self._i += 1
            return tr
        tr = turn_result_from_trace(self._trace, user_message=user_message)
        self._i += 1
        return tr


def scripted_agent(check_id: str) -> AdaptedAgent:
    return ScriptedTraceAgent(check_id)
