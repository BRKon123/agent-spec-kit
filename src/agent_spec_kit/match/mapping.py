"""Normalize structured objects to ``dict[str, Any]`` for object matching."""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping
from typing import Any

from pydantic import BaseModel


def actual_as_mapping(value: Any) -> dict[str, Any] | None:
    """
    Convert a value to a plain string-keyed dict for :class:`ObjectMatcher`.

    Supported:

    - ``dict``
    - :class:`pydantic.BaseModel` (:meth:`~pydantic.BaseModel.model_dump`)
    - :func:`dataclasses.dataclass` instances (:func:`dataclasses.asdict`)
    - other :class:`collections.abc.Mapping` (excluding ``str`` / ``bytes``)
    - :class:`typing.NamedTuple` / ``namedtuple`` instances (``_asdict()``)
    """
    if isinstance(value, dict):
        return value

    if isinstance(value, BaseModel):
        return value.model_dump()

    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return dataclasses.asdict(value)

    if isinstance(value, Mapping) and not isinstance(value, (str, bytes, bytearray)):
        return dict(value)

    # collections.namedtuple / typing.NamedTuple instances
    if getattr(type(value), "_fields", None) is not None and not isinstance(value, type):
        fn = getattr(value, "_asdict", None)
        if callable(fn):
            return fn()

    return None
