"""Generative segment (fuzz / simulate) capture types for the runner."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from agent_spec_kit.run import ConversationTurn

_TURN_AFTER_RE = re.compile(r"after turn #(\d+)", re.I)
_TURN_COMMA_RE = re.compile(r", turn (\d+)", re.I)


def _turn_index_from_counterexample(cx: Any) -> int | None:
    """Parse 0-based turn index from counterexample location fields."""
    for attr in ("location_detail", "location"):
        text = getattr(cx, attr, None)
        if not text:
            continue
        m = _TURN_AFTER_RE.search(str(text))
        if m:
            return int(m.group(1)) - 1
        m = _TURN_COMMA_RE.search(str(text))
        if m:
            return int(m.group(1))
    return None


@dataclass(frozen=True, slots=True)
class FailureSignature:
    """Stable identity for ``same failure`` across reruns."""

    check_kind: str | None
    path: str | None
    assertion_id: str | None
    turn_index: int | None = None

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "check_kind": self.check_kind,
            "path": self.path,
            "assertion_id": self.assertion_id,
        }
        if self.turn_index is not None:
            out["turn_index"] = self.turn_index
        return out

    def equivalence_key(self) -> tuple[str | None, str | None, int | None]:
        """Identity for cross-run / cross-arm failure comparison."""
        return (self.check_kind, self.path, self.turn_index)

    @staticmethod
    def from_dict(d: dict[str, Any] | None) -> FailureSignature | None:
        if d is None:
            return None
        ck, path, aid = d.get("check_kind"), d.get("path"), d.get("assertion_id")
        turn_index = d.get("turn_index")
        if ck is None and path is None and aid is None and turn_index is None:
            return None
        return FailureSignature(
            check_kind=ck,
            path=path,
            assertion_id=aid,
            turn_index=turn_index if turn_index is not None else None,
        )

    @staticmethod
    def from_counterexample(cx: Any) -> FailureSignature:
        return FailureSignature(
            check_kind=getattr(cx, "check_kind", None),
            path=getattr(cx, "path", None),
            assertion_id=None,
            turn_index=_turn_index_from_counterexample(cx),
        )


@dataclass(frozen=True, slots=True)
class CapturedEpisode:
    segment_kind: Literal["fuzz", "simulate"]
    user_turns: tuple[str, ...]
    transcript: tuple[ConversationTurn, ...]
    failure_signature: FailureSignature | None
    seed: int | None
    trial_index: int | None


__all__ = ["CapturedEpisode", "FailureSignature"]
