"""Dataclass and Pydantic model matching."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel

import agent_spec_kit.match as m


@dataclass
class _SampleDataclass:
    name: str
    count: int


@dataclass
class _InnerDc:
    x: int


@dataclass
class _OuterDc:
    inner: _InnerDc


def test_check_dataclass_instance_matches_object_spec() -> None:
    spec = m.object({"name": m.string(min_len=1), "count": 3})
    assert m.check(spec, _SampleDataclass(name="a", count=3)).ok
    r = m.check(spec, _SampleDataclass(name="", count=3))
    assert not r.ok
    assert any(e.path == ("name",) for e in r.errors)


def test_check_nested_dataclass_for_inner_object_spec() -> None:
    spec = m.object({"inner": m.object({"x": 1})})
    assert m.check(spec, _OuterDc(inner=_InnerDc(x=1))).ok
    r = m.check(spec, _OuterDc(inner=_InnerDc(x=2)))
    assert not r.ok
    assert any(e.path == ("inner", "x") for e in r.errors)


def test_check_pydantic_model_matches_object_spec() -> None:
    class _PM(BaseModel):
        name: str
        n: int

    spec = m.object({"name": "hi", "n": m.number(min=0)})
    assert m.check(spec, _PM(name="hi", n=0)).ok
    r = m.check(spec, _PM(name="hi", n=-1))
    assert not r.ok
    assert any(e.path == ("n",) for e in r.errors)


def test_check_pydantic_nested_models_in_object_spec() -> None:
    class _Inner(BaseModel):
        tag: str

    class _Outer(BaseModel):
        inner: _Inner

    spec = m.object({"inner": m.object({"tag": m.string(min_len=1)})})
    assert m.check(spec, _Outer(inner=_Inner(tag="ok"))).ok
    r = m.check(spec, _Outer(inner=_Inner(tag="")))
    assert not r.ok
    assert any(e.path == ("inner", "tag") for e in r.errors)
