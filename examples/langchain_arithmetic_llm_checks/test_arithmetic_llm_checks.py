"""Arithmetic scenario demonstrating LLM criteria checks on outputs and tool results."""

from __future__ import annotations

import agent_spec_kit as ek
import agent_spec_kit.match as m


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("langchain", "example", "arithmetic", "llm-criteria"),
    timeout_s=120.0,
)
async def test_arithmetic_with_llm_criteria_checks(s):
    (
        s.user_message(
            "Compute (4 * 5) + 3. "
            "Use multiply_numbers for 4 and 5, then add_numbers for the product and 3. "
            "Include both intermediate and final numbers in the answer."
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
                m.tool_call(
                    "add_numbers",
                    args={"a": 20, "b": 3},
                    result=m.llm_criteria(
                        criteria=["contains 23"],
                        threshold=1,
                        model="openai:gpt-5-nano",
                    ),
                ),
            ],
            ordered=True,
            allow_extras=True,
        )
        .assert_output(
            m.llm_criteria(
                criteria=[
                    "contains 20",
                    "contains 23",
                    "contains brutus",
                ],
                threshold=3,
                model="openai:gpt-5-nano",
            )
        )
    )
