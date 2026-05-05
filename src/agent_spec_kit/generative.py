"""Generative segment (fuzz / simulate) capture types for the runner."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from agent_spec_kit.run import ConversationTurn


@dataclass(frozen=True, slots=True)
class FailureSignature:
    """Stable identity for ``same failure`` across reruns."""

    check_kind: str | None
    path: str | None
    assertion_id: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "check_kind": self.check_kind,
            "path": self.path,
            "assertion_id": self.assertion_id,
        }

    @staticmethod
    def from_dict(d: dict[str, Any] | None) -> FailureSignature | None:
        if d is None:
            return None
        ck, path, aid = d.get("check_kind"), d.get("path"), d.get("assertion_id")
        if ck is None and path is None and aid is None:
            return None
        return FailureSignature(check_kind=ck, path=path, assertion_id=aid)

    @staticmethod
    def from_counterexample(cx: Any) -> FailureSignature:
        return FailureSignature(
            check_kind=getattr(cx, "check_kind", None),
            path=getattr(cx, "path", None),
            assertion_id=None,
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
