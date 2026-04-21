"""Decorator validation."""

from __future__ import annotations

import pytest

from agent_spec_kit.decorators import scenario
from agent_spec_kit.registries import reset_registries


def test_scenario_rejects_non_s_first_param() -> None:
    reset_registries()

    with pytest.raises(TypeError, match="first parameter.*'s'"):

        @scenario(agent_fixture="agent")
        async def bad(wrong, agent):  # type: ignore[no-untyped-def]
            pass


def test_scenario_agent_fixture_need_not_be_in_signature() -> None:
    reset_registries()

    @scenario(agent_fixture="agent", tags=())
    async def t(s):  # type: ignore[no-untyped-def]
        pass

    assert t.__name__ == "t"
