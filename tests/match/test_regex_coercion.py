"""Tests for regex pattern coercion."""

from __future__ import annotations

import re

import agent_spec_kit.match as m


def test_regex_pattern_coercion() -> None:
    pat = re.compile(r"^[a-z]+$")
    r = m.check(pat, "abc")
    assert r.ok
    assert not m.check(pat, "Abc").ok
