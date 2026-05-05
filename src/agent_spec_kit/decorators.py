"""@fixture, @parametrize, and @scenario registration decorators."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Iterable
from typing import Any, TypeVar, cast, overload

from agent_spec_kit.fuzz_config import ExtractionConfig, ShrinkConfig
from agent_spec_kit.param_cases import Case, normalize_cases
from agent_spec_kit.registries import (
    FixtureDef,
    FixtureParamAxis,
    ScenarioDef,
    register_fixture,
    register_scenario,
)

F = TypeVar("F", bound=Callable[..., Any])
EK_PARAM = "_ek_param_axes"


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


def _axes_from_function(fn: Callable[..., Any]) -> tuple[FixtureParamAxis, ...]:
    raw: list[tuple[str, list[Case[Any]]]] = cast(
        "list[tuple[str, list[Case[Any]]]]", getattr(fn, EK_PARAM, [])
    )
    if not raw:
        return ()
    return tuple(
        FixtureParamAxis(name=n, cases=tuple(c)) for n, c in raw
    )


def parametrize(name: str, values: Iterable[Any]) -> Callable[[F], F]:
    """Stack on an ``@ek.fixture`` (put ``@ek.fixture`` on the **outer** line, parametrize **inner**)."""

    cases = normalize_cases(values)

    def deco(fn: F) -> F:
        cur: list[tuple[str, list[Case[Any]]]] = cast("list", list(getattr(fn, EK_PARAM, [])))
        cur.append((name, list(cases)))
        setattr(fn, EK_PARAM, cur)
        return fn

    return deco


def fixture(fn: F) -> F:
    """Register a fixture (plain return or ``yield`` teardown)."""
    param_axes = _axes_from_function(fn)
    dep_names = _param_names_for_fixture(fn)
    for ax in param_axes:
        if ax.name not in dep_names:
            raise TypeError(
                f"{fn.__name__}: @parametrize({ax.name!r}, ...) but that name is not a parameter of the fixture"
            )
    ax_names = [a.name for a in param_axes]
    if len(ax_names) != len(set(ax_names)):
        raise TypeError(f"{fn.__name__}: duplicate @parametrize axis name in fixture")

    definition = FixtureDef(
        name=fn.__name__,
        fn=fn,
        dep_names=dep_names,
        source=_fixture_source(fn),
        param_axes=param_axes,
    )
    register_fixture(definition)
    return fn


@overload
def scenario(
    *,
    agent_fixture: str | None = None,
    user_fixture: str | None = None,
    repeats: int = 1,
    tags: tuple[str, ...] = (),
    timeout_s: float | None = None,
    shrinking: ShrinkConfig | None = None,
    extraction: ExtractionConfig | None = None,
    regression_id: str | None = None,
) -> Callable[[F], F]: ...


@overload
def scenario(fn: F) -> F: ...


def scenario(
    fn: F | None = None,
    *,
    agent_fixture: str | None = None,
    user_fixture: str | None = None,
    repeats: int = 1,
    tags: tuple[str, ...] = (),
    timeout_s: float | None = None,
    shrinking: ShrinkConfig | None = None,
    extraction: ExtractionConfig | None = None,
    regression_id: str | None = None,
) -> Callable[[F], F] | F:
    """Register a scenario. At least one of ``agent_fixture`` or ``user_fixture`` must be set."""

    def deco(f: F) -> F:
        if agent_fixture is None and user_fixture is None:
            msg = (
                f"{f.__name__}: @scenario() requires at least one of "
                f"agent_fixture=... or user_fixture=..."
            )
            raise TypeError(msg)
        if repeats < 1:
            raise ValueError("repeats must be >= 1")
        if timeout_s is not None and timeout_s <= 0:
            raise ValueError("timeout_s must be > 0 when set")
        if extraction is not None and not extraction.target_file.strip():
            raise TypeError(f"{f.__name__}: extraction.target_file must be non-empty")

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
        # After ``s``: fixture names, @parametrize axis values (name → Case.value), or ``{axis}_case`` (full Case).
        fixture_param_names = tuple(name for name, _ in params[1:])

        definition = ScenarioDef(
            name=f.__name__,
            module=f.__module__,
            fn=f,
            agent_fixture=agent_fixture,
            user_fixture=user_fixture,
            repeats=repeats,
            tags=tags,
            timeout_s=timeout_s,
            source=_fixture_source(f),
            fixture_param_names=fixture_param_names,
            shrinking=shrinking,
            extraction=extraction,
            regression_id=regression_id,
        )
        register_scenario(definition)
        return f

    if fn is not None:
        return deco(fn)
    return deco


__all__ = ["fixture", "parametrize", "scenario"]
