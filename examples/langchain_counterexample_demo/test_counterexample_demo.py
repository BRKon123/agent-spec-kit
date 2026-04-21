"""Counterexample / CLI printing harness for ``agent-spec-kit run`` (live LangChain agent).

Requires ``OPENAI_API_KEY`` and the optional LangChain stack (see project ``dependency-groups``
dev). ``fixtures.py`` in this directory registers the agent and small demo fixtures.

Run from repo root::

    OPENAI_API_KEY=... uv run agent-spec-kit run examples/langchain_counterexample_demo/

Filter by tag::

    uv run agent-spec-kit run examples/langchain_counterexample_demo/ --tags expected-failure
    uv run agent-spec-kit run examples/langchain_counterexample_demo/ --tags demo-pass

Scenarios mix **passing** and **intentionally failing** checks so the Results table and
failure panels exercise ``assert_output``, ``assert_tool_calls``, ``assert_that``, and
plain scenario-body assertions using fixtures.
"""

from __future__ import annotations

import agent_spec_kit as ek
import agent_spec_kit.match as m


def _demo_assert_that_fails_on_env_flag(env_flag_true: bool) -> None:
    assert env_flag_true is False, (
        "demo assert_that: env invariant failed (expected env_flag_true is False)"
    )


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("counterexample-demo", "demo-pass", "langchain"),
    timeout_s=120.0,
)
async def test_counterexample_demo_pass_multiplication_reply_contains_four(s, adapted_agent):
    s.user_message("What is 2 times 2? Reply briefly and include the digit 4 in your answer.")
    await s.materialise()
    s.assert_output(m.contains("4"))
    await s.materialise()


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("counterexample-demo", "expected-failure", "langchain"),
    timeout_s=120.0,
)
async def test_counterexample_demo_fail_assert_output_literal(s, adapted_agent):
    s.user_message("Say hello in one short sentence.")
    await s.materialise()
    s.assert_output("___COUNTEREX_DEMO_IMPOSSIBLE_LITERAL___")
    await s.materialise()


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("counterexample-demo", "expected-failure", "langchain"),
    timeout_s=120.0,
)
async def test_counterexample_demo_fail_tool_calls_missing_sql(s, adapted_agent):
    s.user_message("What is 2 + 3? Reply briefly; you do not need any database.")
    await s.materialise()
    s.assert_tool_calls([m.tool_call("query_sql_database")], ordered=True, allow_extras=False)
    await s.materialise()


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("counterexample-demo", "expected-failure", "langchain"),
    timeout_s=120.0,
)
async def test_counterexample_demo_fail_tool_calls_wrong_args(s, adapted_agent):
    s.user_message(
        "Compute 10 + 20 using the add_integers tool (call it with a=10 and b=20). "
        "Then state the numeric result in natural language."
    )
    await s.materialise()
    s.assert_tool_calls(
        [m.tool_call("add_integers", args={"a": 999, "b": 999})],
        ordered=True,
        allow_extras=False,
    )
    await s.materialise()


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("counterexample-demo", "expected-failure", "langchain"),
    timeout_s=120.0,
)
async def test_counterexample_demo_fail_assert_that_env(s, adapted_agent, env_flag_true):
    (
        s.user_message("Say hi in one short sentence.")
        .assert_that(_demo_assert_that_fails_on_env_flag)
    )
    await s.materialise()


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("counterexample-demo", "expected-failure", "langchain"),
    timeout_s=120.0,
)
async def test_counterexample_demo_fail_body_fixture_substring(s, adapted_agent, wrong_expected_substring):
    s.user_message("Say hello in one short sentence.")
    await s.materialise()
    out = str(s.last_turn.output)
    assert wrong_expected_substring in out, (
        f"demo body assert: expected impossible token in model output (fixture-driven check)"
    )


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("counterexample-demo", "expected-failure", "langchain"),
    timeout_s=120.0,
)
async def test_counterexample_demo_fail_assert_output_regex(s, adapted_agent):
    s.user_message("Say hello in one short sentence.")
    await s.materialise()
    s.assert_output(m.string(pattern=r"^ZZZ+"))
    await s.materialise()


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("counterexample-demo", "expected-failure", "langchain"),
    timeout_s=120.0,
)
async def test_counterexample_demo_fail_tool_calls_ordered_pair_when_only_add(s, adapted_agent):
    s.user_message(
        "Use add_integers only: what is 7 + 8? Call add_integers with a=7 and b=8, then answer briefly."
    )
    await s.materialise()
    s.assert_tool_calls(
        [
            m.tool_call("multiply_integers"),
            m.tool_call("add_integers"),
        ],
        ordered=True,
        allow_extras=False,
    )
    await s.materialise()
