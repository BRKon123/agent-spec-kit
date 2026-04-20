"""Deeply nested integration-style fixture."""

from __future__ import annotations

import agent_spec_kit.match as m


def test_nested_json_fixture() -> None:
    """Deeply nested structure mixing objects, lists, multiset, rules, predicates."""

    spec = m.object(
        {
            "version": 1,
            "payload": {
                "users": m.list_of(
                    m.object(
                        {
                            "id": m.string(min_len=1),
                            "scores": m.list(
                                [
                                    m.number(min=0),
                                    m.number(min=0),
                                    lambda x: x == 100,
                                ],
                                mode="unordered",
                                allow_extras=False,
                            ),
                            "meta": m.optional(
                                m.object(
                                    {
                                        "flag": True,
                                    },
                                    extra="forbid",
                                )
                            ),
                        },
                        extra="forbid",
                    )
                ),
                "tags": m.list(["alpha", "beta"]),
            },
            "audit": m.list_of(
                m.object(
                    {
                        "kind": m.one_of("create", "update"),
                        "ref": lambda x: isinstance(x, str) and len(x) > 0,
                    }
                )
            ),
        },
        rules=[
            m.require("payload").when(m.field("version") == 1),
        ],
        extra="forbid",
    )

    actual = {
        "version": 1,
        "payload": {
            "users": [
                {
                    "id": "u1",
                    "scores": [100, 0, 50],
                    "meta": {"flag": True},
                },
                {
                    "id": "u2",
                    "scores": [50, 100, 0],
                },
            ],
            "tags": ["alpha", "beta"],
        },
        "audit": [
            {"kind": "create", "ref": "a1"},
            {"kind": "update", "ref": "a2"},
        ],
    }
    r = m.check(spec, actual)
    assert r.ok, r.errors

    bad_tags = {
        **actual,
        "payload": {
            **actual["payload"],
            "tags": ["beta", "alpha"],
        },
    }
    r2 = m.check(spec, bad_tags)
    assert not r2.ok
    assert r2.errors
