"""Unit tests for ``-n`` worker resolution."""

from __future__ import annotations

import argparse

import pytest

from agent_spec_kit.parallel_workers import parse_num_workers, resolve_num_workers


def test_parse_num_workers_int() -> None:
    assert parse_num_workers("4") == 4


def test_parse_num_workers_auto() -> None:
    assert parse_num_workers("auto") == "auto"
    assert parse_num_workers("AUTO") == "auto"


def test_parse_num_workers_rejects_invalid() -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        parse_num_workers("0")
    with pytest.raises(argparse.ArgumentTypeError):
        parse_num_workers("nope")


def test_resolve_num_workers_auto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("os.cpu_count", lambda: 8)
    assert resolve_num_workers("auto") == 8


def test_resolve_num_workers_auto_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("os.cpu_count", lambda: None)
    assert resolve_num_workers("auto") == 1


def test_resolve_num_workers_int() -> None:
    assert resolve_num_workers(3) == 3
