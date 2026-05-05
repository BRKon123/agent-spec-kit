from __future__ import annotations

from agent_spec_kit.fuzz.behaviour_grammar import behaviour_grammar
from agent_spec_kit.fuzz.summary import render_trial_summary
from agent_spec_kit.fuzz_config import FuzzConfig, UserAction


def _fuzz_config() -> FuzzConfig:
    strategy = behaviour_grammar((UserAction(name="ask", templates=("hi",)),))
    return FuzzConfig(
        strategy=strategy,
        seed_inputs=("Please summarize this long sentence for me",),
        seed=123,
    )


def test_render_trial_summary_empty_trial() -> None:
    cfg = _fuzz_config()
    got = render_trial_summary(labels=(), details=(), fuzz_config=cfg)
    assert got == "(empty trial)"


def test_render_trial_summary_single_seed_mutation() -> None:
    cfg = _fuzz_config()
    got = render_trial_summary(
        labels=("mutation_of(seed[0])",),
        details=({"template_index": 0},),
        fuzz_config=cfg,
    )
    assert got.startswith('llm-mutation("Please summarize')


def test_render_trial_summary_collapses_repeated_seed_mutation() -> None:
    cfg = _fuzz_config()
    got = render_trial_summary(
        labels=("mutation_of(seed[0])", "mutation_of(seed[0])", "mutation_of(seed[0])"),
        details=({}, {}, {}),
        fuzz_config=cfg,
    )
    assert got.endswith("(×3)")
    assert got.startswith('LLM mutation of "Please summarize')
