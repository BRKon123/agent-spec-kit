"""Registry behaviour."""

from __future__ import annotations

import textwrap

import pytest

from agent_spec_kit.registries import reset_registries


def test_duplicate_fixture_reports_both_sources() -> None:
    reset_registries()
    g1: dict[str, object] = {"__name__": "dup_mod_a"}
    exec(
        textwrap.dedent(
            """
            from agent_spec_kit.decorators import fixture
            @fixture
            def dup():
                return 1
            """
        ),
        g1,
    )
    g2: dict[str, object] = {"__name__": "dup_mod_b"}
    with pytest.raises(RuntimeError, match="duplicate fixture name 'dup'"):
        exec(
            textwrap.dedent(
                """
                from agent_spec_kit.decorators import fixture
                @fixture
                def dup():
                    return 2
                """
            ),
            g2,
        )
