"""Field references and conditional object rules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


class Condition(ABC):
    __slots__ = ()

    @abstractmethod
    def evaluate(self, obj: dict[str, Any]) -> bool:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class FieldEquals(Condition):
    name: str
    value: Any

    def evaluate(self, obj: dict[str, Any]) -> bool:
        return obj.get(self.name) == self.value

    def __repr__(self) -> str:
        return f"field({self.name!r}) == {self.value!r}"


@dataclass(frozen=True, slots=True)
class FieldNotEquals(Condition):
    name: str
    value: Any

    def evaluate(self, obj: dict[str, Any]) -> bool:
        return obj.get(self.name) != self.value

    def __repr__(self) -> str:
        return f"field({self.name!r}) != {self.value!r}"


@dataclass(frozen=True, slots=True)
class FieldCompare(Condition):
    name: str
    op: str  # "<", "<=", ">", ">="
    value: Any

    def __repr__(self) -> str:
        return f"field({self.name!r}) {self.op} {self.value!r}"

    def evaluate(self, obj: dict[str, Any]) -> bool:
        v = obj.get(self.name)
        if self.op == "<":
            return v < self.value
        if self.op == "<=":
            return v <= self.value
        if self.op == ">":
            return v > self.value
        if self.op == ">=":
            return v >= self.value
        raise RuntimeError(f"unknown op {self.op!r}")


class FieldRef:
    """Reference another object key for rule conditions (see :func:`require` / :func:`forbid`).

    Compare with ``==``, ``!=``, or ``<`` / ``<=`` / ``>`` / ``>=`` to build a condition,
    e.g. ``m.field("action") == "escalate"``.
    """

    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name

    def __eq__(self, other: object) -> FieldEquals:  # type: ignore[override]
        return FieldEquals(self.name, other)

    def __ne__(self, other: object) -> FieldNotEquals:  # type: ignore[override]
        return FieldNotEquals(self.name, other)

    def __lt__(self, other: Any) -> FieldCompare:
        return FieldCompare(self.name, "<", other)

    def __le__(self, other: Any) -> FieldCompare:
        return FieldCompare(self.name, "<=", other)

    def __gt__(self, other: Any) -> FieldCompare:
        return FieldCompare(self.name, ">", other)

    def __ge__(self, other: Any) -> FieldCompare:
        return FieldCompare(self.name, ">=", other)


class Rule(ABC):
    __slots__ = ()

    @abstractmethod
    def describe(self) -> str:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class RequireRule(Rule):
    field_name: str
    when: Condition

    def describe(self) -> str:
        return f"require {self.field_name!r} when ({self.when})"


@dataclass(frozen=True, slots=True)
class ForbidRule(Rule):
    field_name: str
    when: Condition

    def describe(self) -> str:
        return f"forbid {self.field_name!r} when ({self.when})"


class _WhenBuilder:
    __slots__ = ("_field_name", "_kind")

    def __init__(self, field_name: str, kind: str) -> None:
        self._field_name = field_name
        self._kind = kind

    def when(self, condition: Condition) -> RequireRule | ForbidRule:
        """Attach when the rule applies (built from :func:`field` comparisons)."""
        if self._kind == "require":
            return RequireRule(field_name=self._field_name, when=condition)
        return ForbidRule(field_name=self._field_name, when=condition)


def require(field_name: str) -> _WhenBuilder:
    """Require ``field_name`` to be present when the ``.when(...)`` condition is true.

    Pass the result in ``object(..., rules=[m.require("ticket_id").when(...), ...])``.
    """
    return _WhenBuilder(field_name, "require")


def forbid(field_name: str) -> _WhenBuilder:
    """Require ``field_name`` to be absent when the ``.when(...)`` condition is true."""
    return _WhenBuilder(field_name, "forbid")


def field(name: str) -> FieldRef:
    """Start a condition on another key of the same object (for use in ``.when(...)``)."""
    return FieldRef(name)
