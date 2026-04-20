"""Tests for transform()."""

from __future__ import annotations

import agent_spec_kit.match as m


def test_transform() -> None:
    spec = m.transform(lambda s: int(s), m.number(int_only=True))
    assert m.check(spec, "7").ok
    assert not m.check(spec, "nope").ok
