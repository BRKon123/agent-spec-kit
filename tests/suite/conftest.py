"""Isolate suite registries between tests."""

from __future__ import annotations

import pytest

from agent_spec_kit.registries import reset_registries


@pytest.fixture(autouse=True)
def _reset_registries() -> object:
    reset_registries()
    yield
    reset_registries()
