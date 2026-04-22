"""Canonical :class:`Case` for parameterisation; used by :func:`parametrize`."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class Case(Generic[T]):
    value: T
    id: str
    name: str | None = None
    meta: Mapping[str, Any] = field(default_factory=dict)


def case(
    value: T,
    *,
    id: str,
    name: str | None = None,
    meta: Mapping[str, Any] | None = None,
) -> Case[T]:
    return Case(
        value=value,
        id=id,
        name=name,
        meta={} if meta is None else dict(meta),
    )


def infer_case_id(value: Any) -> str:
    s = str(value).strip()
    s = s.replace(" ", "_").replace("/", "_")
    return s or "case"


def normalize_case(obj: Any) -> Case[Any]:
    if isinstance(obj, Case):
        return obj

    if hasattr(obj, "id"):
        return Case(
            value=obj,
            id=str(getattr(obj, "id")),
            name=getattr(obj, "name", None),
            meta=dict(getattr(obj, "meta", {}) or {}),
        )

    return Case(
        value=obj,
        id=infer_case_id(obj),
        name=None,
        meta={},
    )


def normalize_cases(values: Iterable[Any]) -> list[Case[Any]]:
    out = [normalize_case(v) for v in values]
    seen: set[str] = set()
    for c in out:
        if c.id in seen:
            msg = f"duplicate case id: {c.id!r}"
            raise ValueError(msg)
        seen.add(c.id)
    return out


__all__ = ["Case", "case", "infer_case_id", "normalize_case", "normalize_cases"]
