"""@fixture and @scenario registration decorators."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any, TypeVar, overload

from agent_spec_kit.registries import FixtureDef, ScenarioDef, register_fixture, register_scenario

F = TypeVar("F", bound=Callable[..., Any])


def _fixture_source(fn: Callable[..., Any]) -> str:
    try:
        return inspect.getfile(fn)
    except TypeError:
        return fn.__module__


def _param_names_for_fixture(fn: Callable[..., Any]) -> tuple[str, ...]:
    sig = inspect.signature(fn)
    names: list[str] = []
    for name, param in sig.parameters.items():
        if param.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            raise TypeError(
                f"{fn.__name__}: *args and **kwargs are not supported on fixtures (got {param!r})"
            )
        names.append(name)
    return tuple(names)


def fixture(fn: F) -> F:
    """Register a fixture function (plain return or ``yield`` teardown)."""
    definition = FixtureDef(
        name=fn.__name__,
        fn=fn,
        dep_names=_param_names_for_fixture(fn),
        source=_fixture_source(fn),
    )
    register_fixture(definition)
    return fn


@overload
def scenario(
    *,
    agent_fixture: str,
    repeats: int = 1,
    tags: tuple[str, ...] = (),
    timeout_s: float | None = None,
) -> Callable[[F], F]: ...


@overload
def scenario(fn: F) -> F: ...


def scenario(
    fn: F | None = None,
    *,
    agent_fixture: str | None = None,
    repeats: int = 1,
    tags: tuple[str, ...] = (),
    timeout_s: float | None = None,
) -> Callable[[F], F] | F:
    """Register a scenario test (metadata only; does not run at import time)."""

    def deco(f: F) -> F:
        if agent_fixture is None:
            raise TypeError("@scenario() requires agent_fixture=...")
        if repeats < 1:
            raise ValueError("repeats must be >= 1")
        if timeout_s is not None and timeout_s <= 0:
            raise ValueError("timeout_s must be > 0 when set")

        sig = inspect.signature(f)
        params = list(sig.parameters.items())
        for _name, param in params:
            if param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                raise TypeError(
                    f"{f.__name__}: *args and **kwargs are not supported on scenario callables"
                )
        if not params:
            raise TypeError(f"{f.__name__}: scenario callable must have first parameter named 's'")
        first_name, _first = params[0]
        if first_name != "s":
            raise TypeError(
                f"{f.__name__}: first parameter of a scenario must be named 's' (got {first_name!r})"
            )
        fixture_param_names = tuple(name for name, _ in params[1:])

        definition = ScenarioDef(
            name=f.__name__,
            module=f.__module__,
            fn=f,
            agent_fixture=agent_fixture,
            repeats=repeats,
            tags=tags,
            timeout_s=timeout_s,
            source=_fixture_source(f),
            fixture_param_names=fixture_param_names,
        )
        register_scenario(definition)
        return f

    if fn is not None:
        return deco(fn)
    return deco


__all__ = ["fixture", "scenario"]
