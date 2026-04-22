"""Unit tests for :mod:`agent_spec_kit.param_cases`."""

from __future__ import annotations

import pytest

import agent_spec_kit as ek
from agent_spec_kit.param_cases import Case, infer_case_id, normalize_case, normalize_cases


def test_case_explicit() -> None:
    c = ek.case("gpt-4.1", id="gpt41", name="n", meta={"k": 1})
    assert isinstance(c, Case)
    assert c.value == "gpt-4.1"
    assert c.id == "gpt41"
    assert c.name == "n"
    assert dict(c.meta) == {"k": 1}


def test_normalize_raw() -> None:
    c = normalize_case("a/b c")
    assert c.value == "a/b c"
    assert c.id == "a_b_c"


def test_normalize_object_with_id() -> None:
    class T:
        id = "t1"
        name = "T"
        meta = {"d": 1}

    c = normalize_case(T())
    assert c.value is not None
    assert c.id == "t1"
    assert c.name == "T"
    assert c.meta == {"d": 1}


def test_duplicate_ids_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate case id"):
        normalize_cases([ek.case(1, id="x"), ek.case(2, id="x")])


def test_infer_empty_string() -> None:
    assert infer_case_id("   \n  ") == "case"
