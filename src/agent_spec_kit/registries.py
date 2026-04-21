"""Suite-level registries populated by decorators (one interpreter / CLI run)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class FixtureDef:
    name: str
    fn: Callable[..., Any]
    dep_names: tuple[str, ...]
    source: str


@dataclass(frozen=True, slots=True)
class ScenarioDef:
    name: str
    module: str
    fn: Callable[..., Any]
    agent_fixture: str
    repeats: int
    tags: tuple[str, ...]
    timeout_s: float | None
    source: str
    fixture_param_names: tuple[str, ...]


_fixtures: dict[str, FixtureDef] = {}
_scenarios: list[ScenarioDef] = []


def reset_registries() -> None:
    _fixtures.clear()
    _scenarios.clear()


def register_fixture(definition: FixtureDef) -> None:
    existing = _fixtures.get(definition.name)
    if existing is not None:
        msg = (
            f"duplicate fixture name {definition.name!r}:\n"
            f"  first:  {existing.source}\n"
            f"  second: {definition.source}"
        )
        raise RuntimeError(msg)
    _fixtures[definition.name] = definition


def register_scenario(definition: ScenarioDef) -> None:
    _scenarios.append(definition)


def get_fixture(name: str) -> FixtureDef | None:
    return _fixtures.get(name)


def iter_fixtures() -> tuple[FixtureDef, ...]:
    return tuple(_fixtures.values())


def iter_scenarios() -> tuple[ScenarioDef, ...]:
    return tuple(_scenarios)


def find_scenario(*, module: str, name: str) -> ScenarioDef | None:
    for s in _scenarios:
        if s.module == module and s.name == name:
            return s
    return None


__all__ = [
    "FixtureDef",
    "ScenarioDef",
    "get_fixture",
    "iter_fixtures",
    "find_scenario",
    "iter_scenarios",
    "register_fixture",
    "register_scenario",
    "reset_registries",
]
