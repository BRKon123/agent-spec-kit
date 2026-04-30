"""Scenario example: assert structured agent output with `assert_output`."""

from __future__ import annotations

import agent_spec_kit as ek
import agent_spec_kit.match as m


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("example", "structured-output", "hardcoded"),
    timeout_s=30.0,
)
async def test_hardcoded_structured_output_assertion(s):
    (
        s.user_message("Plan a short Lisbon trip in structured JSON.")
        .assert_output(
            m.object(
                {
                    "status": "ok",
                    "task": "plan_trip",
                    "destination": "Lisbon",
                    "days": 3,
                    "itinerary": m.list_of(
                        m.object(
                            {
                                "day": m.number(),
                                "activity": m.string(min_len=3),
                            }
                        )
                    ),
                }
            )
        )
        .assert_output(
            m.object(
                {
                    "status": "ok",
                    "task": "plan_trip",
                    "destination": "Lisbon",
                    "days": 3,
                    "itinerary": m.list_of(
                        m.object(
                            {
                                "day": m.number(),
                                "activity": m.string(min_len=3),
                            }
                        )
                    ),
                }
            )
        )
        .assert_tool_calls(
            [
            ],
            ordered=True,
            allow_extras=True,
        )
        .assert_tool_calls(
            [
            ],
            ordered=True,
            allow_extras=True,
        )
    )

    (
        s.user_message("Plan a short Lisbon trip in structured JSON.")
        .assert_output(
            m.object(
                {
                    "status": "ok",
                    "task": "plan_trip",
                    "destination": "Lisbon",
                    "days": 3,
                    "itinerary": m.list_of(
                        m.object(
                            {
                                "day": m.number(),
                                "activity": m.string(min_len=3),
                            }
                        )
                    ),
                }
            )
        )
        .assert_output(
            m.object(
                {
                    "status": "ok",
                    "task": "plan_trip",
                    "destination": "Lisbon",
                    "days": 3,
                    "itinerary": m.list_of(
                        m.object(
                            {
                                "day": m.number(),
                                "activity": m.string(min_len=3),
                            }
                        )
                    ),
                }
            )
        )
        .assert_tool_calls(
            [
            ],
            ordered=True,
            allow_extras=True,
        )
        .assert_tool_calls(
            [
                m.tool_call(
                    "multiply_numbers",
                    args={"a": 4, "b": 5},
                    result=m.llm_criteria(
                        criteria=["contains 20"],
                        threshold=1,
                        model="openai:gpt-5-nano",
                    ),
                ),
            ],
            ordered=True,
            allow_extras=True,
        )
    )

