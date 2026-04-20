"""Matcher protocol and coercion from literals / callables."""

from __future__ import annotations

import inspect
import re
from abc import ABC, abstractmethod
from collections.abc import Mapping
from functools import partial
from typing import Any

from agent_spec_kit.match.types import MatchResult, Path


class BaseMatcher(ABC):
    """All matchers implement :meth:`check`."""

    __slots__ = ()

    @abstractmethod
    def check(self, actual: Any, path: Path) -> MatchResult:
        raise NotImplementedError


def _is_predicate_callable(obj: Any) -> bool:
    """Treat user functions/lambdas/methods/partials as predicates; not types or builtins."""
    if not callable(obj):
        return False
    if isinstance(obj, type):
        return False
    if inspect.isfunction(obj):
        return True
    if inspect.ismethod(obj):
        return True
    if isinstance(obj, partial):
        return True
    return False


def coerce_any(spec: Any) -> BaseMatcher:
    """
    Coerce a public spec value into a matcher.

    - Already a :class:`BaseMatcher` → unchanged
    - ``str``, ``int``, ``float``, ``bool``, ``None`` → equality
    - :class:`re.Pattern` → regex matcher (same as ``m.regex``)
    - Predicate-style callables → :class:`PredicateMatcher` with a generic message
    - :class:`collections.abc.Mapping` (e.g. plain ``dict``) → :func:`object_matcher` with coerced values
    - ``list`` / ``tuple`` → ordered exact-length :func:`list_matcher` with coerced elements
    """
    if isinstance(spec, BaseMatcher):
        return spec

    if isinstance(spec, Mapping):
        from agent_spec_kit.match.object import object_matcher

        return object_matcher({k: coerce_any(v) for k, v in spec.items()})

    if isinstance(spec, (list, tuple)):
        from agent_spec_kit.match.lists import list_matcher

        return list_matcher(spec, mode="ordered", allow_extras=False)

    if isinstance(spec, (str, int, float, bool)) or spec is None:
        from agent_spec_kit.match.scalars import EqualityMatcher

        return EqualityMatcher(spec)

    if isinstance(spec, re.Pattern):
        from agent_spec_kit.match.scalars import RegexMatcher

        return RegexMatcher(spec)

    if _is_predicate_callable(spec):
        from agent_spec_kit.match.scalars import PredicateMatcher

        return PredicateMatcher(spec, message=None)

    raise TypeError(
        f"cannot coerce {type(spec).__name__!r} to a matcher; wrap it explicitly or use a supported literal/callable"
    )
