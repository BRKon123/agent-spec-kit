"""Resolve fixture dependency graphs and build teardown stacks."""

from __future__ import annotations

import inspect
from collections import deque
from collections.abc import Callable, Coroutine
from typing import Any

from agent_spec_kit.registries import FixtureDef, ScenarioDef, get_fixture


async def _invoke_plain_fixture(fn: Callable[..., Any], kwargs: dict[str, Any]) -> Any:
    if inspect.iscoroutinefunction(fn):
        return await fn(**kwargs)
    result = fn(**kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


TeardownFn = Callable[[], Coroutine[Any, Any, None]]


def _collect_needed_fixture_names(scenario: ScenarioDef) -> set[str]:
    needed: set[str] = set(scenario.fixture_param_names)
    needed.add(scenario.agent_fixture)
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
            if dep not in needed:
                needed.add(dep)
                queue.append(dep)
    return needed


def _topo_fixture_order(needed: set[str]) -> list[str]:
    fixture_map: dict[str, FixtureDef] = {}
    for name in needed:
        fd = get_fixture(name)
        assert fd is not None
        fixture_map[name] = fd

    dependents: dict[str, set[str]] = {n: set() for n in needed}
    in_degree: dict[str, int] = {n: 0 for n in needed}
    for name in needed:
        fd = fixture_map[name]
        for dep in fd.dep_names:
            if dep not in needed:
                raise KeyError(
                    f"fixture {name!r} depends on {dep!r} which is not a registered fixture "
                    f"and not a scenario parameter"
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


async def _run_teardowns(teardowns: list[TeardownFn]) -> None:
    for td in reversed(teardowns):
        try:
            await td()
        except Exception:
            pass


async def resolve_fixtures(scenario: ScenarioDef) -> tuple[dict[str, Any], list[TeardownFn]]:
    """Build ``fixture_values`` and a teardown stack (call teardowns in reverse order)."""
    needed = _collect_needed_fixture_names(scenario)
    order = _topo_fixture_order(needed)
    values: dict[str, Any] = {}
    teardowns: list[TeardownFn] = []

    try:
        for name in order:
            fd = get_fixture(name)
            assert fd is not None
            kwargs = {dep: values[dep] for dep in fd.dep_names}
            fn = fd.fn

            if inspect.isasyncgenfunction(fn):
                agen = fn(**kwargs)
                try:
                    value = await anext(agen)
                except StopAsyncIteration as e:
                    value = e.value

                async def _td_ag(g: Any = agen) -> None:
                    try:
                        await anext(g)
                    except StopAsyncIteration:
                        pass
                    try:
                        await g.aclose()
                    except BaseException:
                        pass

                teardowns.append(_td_ag)
                values[name] = value
                continue

            if inspect.isgeneratorfunction(fn):
                gen = fn(**kwargs)
                try:
                    value = next(gen)
                except StopIteration as e:
                    values[name] = e.value
                    continue

                async def _td_g(g: Any = gen) -> None:
                    try:
                        next(g)
                    except StopIteration:
                        pass
                    try:
                        g.close()
                    except Exception:
                        pass

                teardowns.append(_td_g)
                values[name] = value
                continue

            values[name] = await _invoke_plain_fixture(fn, kwargs)
    except BaseException:
        await _run_teardowns(teardowns)
        raise

    return values, teardowns


__all__ = ["resolve_fixtures", "TeardownFn"]
