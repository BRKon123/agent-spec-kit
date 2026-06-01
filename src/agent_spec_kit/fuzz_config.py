"""Fuzz, shrink, and extraction configuration dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent_spec_kit.fuzz_types import Strategy


@dataclass(frozen=True, slots=True)
class UserAction:
    """One behavioral intent with concrete phrasings for behaviour_grammar."""

    name: str
    templates: tuple[str, ...]
    tags: tuple[str, ...] = ()
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("UserAction.name must be non-empty")
        if not self.templates:
            raise ValueError("UserAction.templates must be non-empty")
        if any(not t.strip() for t in self.templates):
            raise ValueError("UserAction.templates must not contain empty strings")
        if self.weight <= 0:
            raise ValueError("UserAction.weight must be > 0")


@dataclass(frozen=True, slots=True)
class FuzzConfig:
    """Per-scenario fuzz generation: strategy + seeds."""

    strategy: Strategy
    seed_inputs: tuple[str, ...] = ()
    seed: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "seed_inputs", tuple(self.seed_inputs))


@dataclass(frozen=True, slots=True)
class ShrinkPassSpec:
    """Opaque shrink pass handle (implemented in agent_spec_kit.shrink)."""

    kind: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ShrinkConfig:
    """Scenario-level shrinking policy (activated by CLI ``--shrink``)."""

    passes: tuple[ShrinkPassSpec, ...]
    confirm_runs: int = 3
    min_reproductions: int = 2
    #: Cap total shrink verification batches per failure (``None`` = unlimited).
    max_attempts_per_shrink: int | None = None

    def __post_init__(self) -> None:
        # Be forgiving for common Python tuple footgun:
        # passes=(remove_user_turns())  # missing trailing comma
        if isinstance(self.passes, ShrinkPassSpec):
            object.__setattr__(self, "passes", (self.passes,))
        else:
            object.__setattr__(self, "passes", tuple(self.passes))
        if not self.passes:
            raise ValueError("ShrinkConfig.passes must be non-empty")
        if self.confirm_runs < 1:
            raise ValueError("ShrinkConfig.confirm_runs must be >= 1")
        if self.min_reproductions < 1:
            raise ValueError("ShrinkConfig.min_reproductions must be >= 1")
        if self.max_attempts_per_shrink is not None and self.max_attempts_per_shrink < 1:
            raise ValueError("ShrinkConfig.max_attempts_per_shrink must be >= 1 when set")


DuplicatePolicy = str  # "skip" | "replace" | "append_variant" | "error"
AssertionPolicy = str  # "failed_only" | "all_after_fuzz"


@dataclass(frozen=True, slots=True)
class ExtractionConfig:
    """Where and how to write generated regression scenarios (activated by CLI ``--extract``)."""

    target_file: str
    mode: str = "append_scenario"
    duplicate_policy: DuplicatePolicy = "skip"
    add_tags: tuple[str, ...] = ()
    assertion_policy: AssertionPolicy = "failed_only"

    def __post_init__(self) -> None:
        if not self.target_file.strip():
            raise ValueError("ExtractionConfig.target_file must be non-empty")
        if self.duplicate_policy not in {"skip", "replace", "append_variant", "error"}:
            raise ValueError(f"unknown duplicate_policy: {self.duplicate_policy!r}")
        if self.assertion_policy not in {"failed_only", "all_after_fuzz"}:
            raise ValueError(f"unknown assertion_policy: {self.assertion_policy!r}")


__all__ = [
    "AssertionPolicy",
    "DuplicatePolicy",
    "ExtractionConfig",
    "FuzzConfig",
    "ShrinkConfig",
    "ShrinkPassSpec",
    "UserAction",
]
