"""Object-shaped matchers with extra keys and conditional rules."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from agent_spec_kit.match.mapping import actual_as_mapping
from agent_spec_kit.match.protocol import BaseMatcher, coerce_any
from agent_spec_kit.match.rules import ForbidRule, RequireRule, Rule
from agent_spec_kit.match.scalars import OptionalMatcher
from agent_spec_kit.match.types import MatchError, MatchResult, Path, _short_repr

ExtraPolicy = Literal["forbid", "ignore"]


@dataclass(frozen=True, slots=True)
class ObjectMatcher(BaseMatcher):
    """Match dict-like values with optional key policy and rules."""

    props: dict[str, BaseMatcher]
    extra: ExtraPolicy = "forbid"
    rules: tuple[Rule, ...] = ()
    where_hooks: tuple[tuple[Callable[[dict[str, Any]], bool], str], ...] = ()

    def where(
        self,
        fn: Callable[[dict[str, Any]], bool],
        message: str,
    ) -> ObjectMatcher:
        """Add an arbitrary whole-object predicate (escape hatch)."""
        return ObjectMatcher(
            props=self.props,
            extra=self.extra,
            rules=self.rules,
            where_hooks=self.where_hooks + ((fn, message),),
        )

    def check(self, actual: Any, path: Path) -> MatchResult:
        obj = actual_as_mapping(actual)
        if obj is None:
            return MatchResult.failure(
                MatchError(
                    path=path,
                    code="object",
                    message="expected a dict or mapping-like object (dict, dataclass, pydantic BaseModel, Mapping, …)",
                    expected="dict-like",
                    actual=type(actual).__name__,
                )
            )
        errors: list[MatchError] = []

        # Declared keys
        for key, matcher in self.props.items():
            is_optional = isinstance(matcher, OptionalMatcher)
            if key not in obj:
                if is_optional:
                    continue
                errors.append(
                    MatchError(
                        path=path + (key,),
                        code="missing_key",
                        message=f"missing required key {key!r}",
                        expected=f"key {key!r}",
                        actual="(absent)",
                    )
                )
                continue
            r = matcher.check(obj[key], path + (key,))
            if not r.ok:
                errors.extend(r.errors)

        # Extra keys
        if self.extra == "forbid":
            for key in obj:
                if key not in self.props:
                    errors.append(
                        MatchError(
                            path=path + (key,),
                            code="extra_key",
                            message=f"unexpected key {key!r}",
                            expected="no extra keys",
                            actual=_short_repr(obj[key]),
                        )
                    )

        if errors:
            return MatchResult(ok=False, errors=tuple(errors))

        # Conditional rules (after per-field success)
        for rule in self.rules:
            if isinstance(rule, RequireRule):
                if rule.when.evaluate(obj):
                    if rule.field_name not in obj:
                        errors.append(
                            MatchError(
                                path=path + (rule.field_name,),
                                code="conditional_rule",
                                message=rule.describe(),
                                expected=f"key {rule.field_name!r} present",
                                actual="(absent)",
                            )
                        )
            elif isinstance(rule, ForbidRule):
                if rule.when.evaluate(obj):
                    if rule.field_name in obj:
                        errors.append(
                            MatchError(
                                path=path + (rule.field_name,),
                                code="conditional_rule",
                                message=rule.describe(),
                                expected=f"key {rule.field_name!r} absent",
                                actual=_short_repr(obj[rule.field_name]),
                            )
                        )

        if errors:
            return MatchResult(ok=False, errors=tuple(errors))

        for fn, msg in self.where_hooks:
            try:
                ok = bool(fn(obj))
            except Exception as e:  # noqa: BLE001
                errors.append(
                    MatchError(
                        path=path,
                        code="where",
                        message=f"where predicate raised: {e}",
                        expected=msg,
                        actual=_short_repr(obj),
                    )
                )
                continue
            if not ok:
                errors.append(
                    MatchError(
                        path=path,
                        code="where",
                        message=msg,
                        expected=msg,
                        actual=_short_repr(obj),
                    )
                )

        if errors:
            return MatchResult(ok=False, errors=tuple(errors))
        return MatchResult.success()


def object_matcher(
    mapping: Mapping[str, Any],
    *,
    extra: ExtraPolicy = "forbid",
    rules: Sequence[Rule] | None = None,
    where: Sequence[tuple[Callable[[dict[str, Any]], bool], str]] | None = None,
) -> ObjectMatcher:
    props = {k: coerce_any(v) for k, v in mapping.items()}
    return ObjectMatcher(
        props=props,
        extra=extra,
        rules=tuple(rules or ()),
        where_hooks=tuple(where or ()),
    )
