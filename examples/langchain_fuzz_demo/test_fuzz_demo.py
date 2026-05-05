"""Fuzz, shrink, and regression extraction demo (live LangChain).

Requires ``OPENAI_API_KEY`` and the LangChain stack (``dependency-groups`` dev).

Run from repo root::

    OPENAI_API_KEY=... uv run agent-spec-kit run examples/langchain_fuzz_demo/

With shrinking (per-trial isolation)::

    OPENAI_API_KEY=... uv run agent-spec-kit run examples/langchain_fuzz_demo/ --shrink

With shrinking + extraction (writes ``regressions/extracted.py``)::

    OPENAI_API_KEY=... uv run agent-spec-kit run examples/langchain_fuzz_demo/ --shrink --extract
"""

from __future__ import annotations

import agent_spec_kit as ek
import agent_spec_kit.match as m

# Skew toward off-topic lines so the last agent turn often has no ``multiply_integers``
# call (``assert_tool_calls`` only inspects the *last* agent turn).
_BEHAVIOUR = ek.fuzz.behaviour_grammar(
    (
        ek.fuzz.user_action(
            "multiply_in_range",
            templates=(
                "What is 3 times 4?",
                "Compute 7 * 2.",
                "Multiply 6 and 5.",
            ),
            weight=1.0,
        ),
        ek.fuzz.user_action(
            "nonsense",
            templates=(
                "Tell me a joke about cats.",
                "What's the weather in Paris today?",
            ),
            weight=8.0,
        ),
    )
)

_FUZZ = ek.FuzzConfig(strategy=_BEHAVIOUR, seed=41)

_SHRINK = ek.ShrinkConfig(
    passes=(ek.shrink.remove_user_turns(),), # ek.shrink.simplify_user_messages()
    confirm_runs=1,
    min_reproductions=1,
)

_EXTRACT = ek.ExtractionConfig(
    target_file="regressions/test_extracted.py",
    add_tags=("regression", "fuzz-demo"),
)


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("langchain", "example", "fuzz-demo", "baseline"),
    timeout_s=90.0,
)
async def test_multiply_baseline_passes(s):
    """Scripted multiply; no fuzz (compare page keeps this row)."""
    (
        s.user_message(
            "What is 5 times 6? Use multiply_integers with a=5 and b=6 only, "
            "then reply briefly and include the digit sequence for the product."
        )
        .assert_tool_calls(
            [m.tool_call("multiply_integers", args={"a": 5, "b": 6})],
            ordered=True,
            allow_extras=True,
        )
        .assert_output(m.contains("30"))
    )


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("langchain", "example", "fuzz-demo", "fuzz", "strict"),
    timeout_s=120.0,
    shrinking=_SHRINK,
    extraction=_EXTRACT,
)
async def test_multiply_fuzz_strict_assert(s):
    """Fuzz + strict tool assertion; use ``--shrink`` / ``--extract`` to exercise the pipeline.

    One trial × several user lines (mostly off-topic) so the last agent turn often
    lacks a ``multiply_integers`` call and the strict matcher fails without flags.
    """
    (
        s.fuzz_conversation(fuzz_config=_FUZZ, trials=3, max_user_turns=5)
        .assert_tool_calls(
            [
                m.tool_call(
                    "multiply_integers",
                    args={
                        "a": m.number(min=0, max=10, int_only=True),
                        "b": m.number(min=0, max=10, int_only=True),
                    },
                )
            ],
            ordered=True,
            allow_extras=False,
            actor="agent",
        )
    )


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("langchain", "example", "fuzz-demo", "fuzz", "lenient"),
    timeout_s=120.0,
)
async def test_multiply_fuzz_lenient(s):
    """Same fuzz mix but only require a non-trivial agent reply (passes without ``--shrink``)."""
    (
        s.fuzz_conversation(fuzz_config=_FUZZ, trials=3, max_user_turns=2)
        .assert_output(m.string(min_len=5), actor="agent")
    )


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("langchain", "example", "fuzz-demo", "fuzz", "scripted-then-fuzz"),
    timeout_s=120.0,
)
async def test_multiply_scripted_setup_then_fuzz(s):
    """Scripted user line, then a short fuzz segment (demos step mixing + generative orchestrator)."""
    (
        s.user_message("Let's practice multiplication briefly.")
        .fuzz_conversation(fuzz_config=_FUZZ, trials=1, max_user_turns=3)
        .assert_output(m.string(min_len=3), actor="agent")
    )
