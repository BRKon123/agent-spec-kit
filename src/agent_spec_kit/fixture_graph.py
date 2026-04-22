"""Resolve fixture dependency graphs, build teardown stacks, and param expansion."""

from __future__ import annotations

import inspect
from collections import deque
from collections.abc import Callable, Coroutine
from itertools import product
from typing import Any

from agent_spec_kit.param_cases import Case
from agent_spec_kit.registries import FixtureDef, ScenarioDef, get_fixture


async def _invoke_plain_fixture(fn: Callable[..., Any], kwargs: dict[str, Any]) -> Any:
    if inspect.iscoroutinefunction(fn):
        return await fn(**kwargs)
    result = fn(**kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


TeardownFn = Callable[[], Coroutine[Any, Any, None]]


def _is_fixture(n: str) -> bool:
    return get_fixture(n) is not None


def _collect_needed_fixture_names(scenario: ScenarioDef) -> set[str]:
    # Only @fixture names (param axes like ``task`` and ``task_case`` are supplied by the runner, not BFS here).
    needed: set[str] = {n for n in scenario.fixture_param_names if _is_fixture(n)}
    if scenario.agent_fixture is not None:
        needed.add(scenario.agent_fixture)
    if scenario.user_fixture is not None:
        needed.add(scenario.user_fixture)
    queue: deque[str] = deque(needed)
    while queue:
        name = queue.popleft()
        fd = get_fixture(name)
        if fd is None:
            raise KeyError(
                f"unknown fixture {name!r} required by scenario {scenario.name!r} "
                f"(from {scenario.source})"
            )
        for dep in fd.dep_names:
            if _is_fixture(dep):
                if dep not in needed:
                    needed.add(dep)
                    queue.append(dep)
    return needed


def _topo_fixture_order(needed: set[str]) -> list[str]:
    fixture_map: dict[str, FixtureDef] = {}
    for name in needed:
        fd = get_fixture(name)
        if fd is None:  # pragma: no cover
            raise KeyError
        fixture_map[name] = fd

    dependents: dict[str, set[str]] = {n: set() for n in needed}
    in_degree: dict[str, int] = {n: 0 for n in needed}
    for name in needed:
        fd = fixture_map[name]
        for dep in fd.dep_names:
            if not _is_fixture(dep):
                continue
            if dep not in needed:
                raise KeyError(
                    f"fixture {name!r} depends on {dep!r} which is not a registered fixture"
                )
            dependents[dep].add(name)
            in_degree[name] += 1

    order: list[str] = []
    ready = deque([n for n in needed if in_degree[n] == 0])
    while ready:
        n = ready.popleft()
        order.append(n)
        for m in dependents[n]:
            in_degree[m] -= 1
            if in_degree[m] == 0:
                ready.append(m)

    if len(order) != len(needed):
        raise RuntimeError(f"cycle in fixture dependencies involving: {sorted(needed)}")
    return order


def _merge_param_axes(needed: set[str], topo_order: list[str]) -> tuple[list[str], dict[str, tuple[Case[Any], ...]]]:
    name_order: list[str] = []
    merged: dict[str, tuple[Case[Any], ...]] = {}
    for fname in topo_order:
        if fname not in needed:  # pragma: no cover
            continue
        fd = get_fixture(fname)
        if fd is None:
            continue
        for ax in fd.param_axes:
            if ax.name not in merged:
                merged[ax.name] = ax.cases
                name_order.append(ax.name)
            else:
                o, n = merged[ax.name], ax.cases
                if len(o) != len(n) or [c.id for c in o] != [c.id for c in n]:
                    msg = f"inconsistent @parametrize cases for {ax.name!r} across fixtures"
                    raise ValueError(msg)
    return name_order, merged


def iter_param_case_combinations(needed: set[str], topo_order: list[str]) -> list[dict[str, Case[Any]]]:
    name_order, merged = _merge_param_axes(needed, topo_order)
    if not merged:
        return [{}]
    keys = [k for k in name_order if k in merged]
    combos = product(*(merged[k] for k in keys))
    return [dict(zip(keys, t, strict=True)) for t in combos]


def scenario_case_runs(scenario: ScenarioDef) -> list[dict[str, Case[Any]]]:
    needed = _collect_needed_fixture_names(scenario)
    order = _topo_fixture_order(needed)
    return iter_param_case_combinations(needed, order)


def _dep_value(
    dep: str, *, values: dict[str, Any], param_case: dict[str, Case[Any]]
) -> Any:
    if dep in param_case:
        if dep in values:
            msg = f"name {dep!r} is both a @parametrize axis and a fixture; use distinct names"
            raise ValueError(msg)
        return param_case[dep].value
    if dep in values:
        return values[dep]
    raise KeyError(
        f"could not resolve dependency {dep!r} (not in param_case and not a resolved fixture). "
        f"param_case keys: {sorted(param_case.keys())!r}, values keys: {sorted(values.keys())!r}"
    )


async def _run_teardowns(teardowns: list[TeardownFn]) -> None:
    for td in reversed(teardowns):
        try:
            await td()
        except Exception:  # noqa: S110
            pass


async def resolve_fixtures(
    scenario: ScenarioDef,
    *,
    param_case: dict[str, Case[Any]] | None = None,
) -> tuple[dict[str, Any], list[TeardownFn]]:
    """Build ``fixture_values`` and a teardown stack."""
    case = dict(param_case or {})
    needed = _collect_needed_fixture_names(scenario)
    order = _topo_fixture_order(needed)
    _, merged = _merge_param_axes(needed, order)
    if merged and set(case.keys()) != set(merged.keys()):
        msg = f"param_case keys {sorted(case.keys())!r} != expected axes {sorted(merged.keys())!r}"
        raise ValueError(msg)
    if not merged and case:
        msg = f"unexpected param_case keys (no @parametrize axes in graph): {sorted(case.keys())!r}"
        raise ValueError(msg)

    values: dict[str, Any] = {}
    teardowns: list[TeardownFn] = []

    try:
        for name in order:
            fd = get_fixture(name)
            assert fd is not None
            kwargs = {dep: _dep_value(dep, values=values, param_case=case) for dep in fd.dep_names}
            fn = fd.fn

            if inspect.isasyncgenfunction(fn):
                agen = fn(**kwargs)  # type: ignore[call-arg]
                try:
                    value = await anext(agen)  # type: ignore[arg-type,unused-ignore]
                except StopAsyncIteration as e:
                    value = e.value  # type: ignore[assignment,unused-ignore]

                async def _td_ag(
                    g: Any = agen,  # noqa: B008
                ) -> None:  # pragma: no cover
                    try:
                        await anext(g)  # type: ignore[call-arg,unused-ignore]
                    except StopAsyncIteration:
                        pass
                    try:
                        await g.aclose()  # type: ignore[func-returns-value,unused-ignore]
                    except BaseException:  # noqa: S110
                        pass

                teardowns.append(_td_ag)  # type: ignore[arg-type]
                values[name] = value
                continue

            if inspect.isgeneratorfunction(fn):
                gen = fn(**kwargs)  # type: ignore[call-arg]
                try:
                    value = next(gen)  # type: ignore[call-overload]
                except StopIteration as e:  # noqa: SIM105
                    values[name] = e.value  # type: ignore[assignment,attr-defined]
                    continue

                def _td_g(
                    g: Any = gen,  # noqa: B008
                ) -> None:  # pragma: no cover
                    try:
                        next(g)
                    except StopIteration:  # noqa: SIM105
                        pass
                    try:
                        g.close()
                    except Exception:  # noqa: S110
                        pass

                teardowns.append(_td_g)  # type: ignore[arg-type]
                values[name] = value
                continue

            values[name] = await _invoke_plain_fixture(fn, kwargs)  # type: ignore[assignment,unused-ignore]
    except BaseException:  # noqa: BLE001
        await _run_teardowns(teardowns)
        raise

    return values, teardowns


__all__ = ["resolve_fixtures", "scenario_case_runs", "TeardownFn", "iter_param_case_combinations"]
