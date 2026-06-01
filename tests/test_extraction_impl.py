from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any
from collections.abc import Sequence

import pytest

from agent_spec_kit.extraction_impl import extract_regression
from agent_spec_kit.fuzz.behaviour_grammar import behaviour_grammar
from agent_spec_kit.fuzz_config import ExtractionConfig, FuzzConfig, UserAction
from agent_spec_kit.registries import ScenarioDef
from agent_spec_kit.scenario_core import (
    _ActionStep,
    _EnvAssertStep,
    _FuzzConversationStep,
    _SimulateStep,
    _UserMessageStep,
)


def _dummy_scenario(tmp_py: Path) -> ScenarioDef:
    def _fn(s, agent):  # noqa: ARG001
        pass

    return ScenarioDef(
        name="demo",
        module="tests",
        fn=_fn,
        agent_fixture="agent",
        user_fixture=None,
        repeats=1,
        tags=(),
        timeout_s=None,
        source=str(tmp_py),
        fixture_param_names=("agent",),
    )


def test_extract_regression_appends_scenario(tmp_path: Path) -> None:
    src = tmp_path / "scenarios" / "base.py"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("# base\n", encoding="utf-8")
    sd = _dummy_scenario(src)
    ext = ExtractionConfig(target_file="regressions/out.py")
    out = extract_regression(
        scenario_def=sd,
        shrunk_user_turns=("hello", "world"),
        failure_signature={"check_kind": "x"},
        extraction=ext,
        regression_id="reg_test_1",
    )
    assert out.status == "written"
    target = src.parent / "regressions" / "out.py"
    assert target.exists()
    text = target.read_text(encoding="utf-8")
    assert "reg_test_1" in text
    assert "s.user_message" in text
    assert "await s.user_message" not in text


def test_extract_regression_skip_duplicate(tmp_path: Path) -> None:
    src = tmp_path / "scenarios" / "base.py"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text("# base\n", encoding="utf-8")
    sd = _dummy_scenario(src)
    ext = ExtractionConfig(target_file="regressions/out.py", duplicate_policy="skip")
    extract_regression(
        scenario_def=sd,
        shrunk_user_turns=("a",),
        failure_signature={},
        extraction=ext,
        regression_id="reg_dup",
    )
    second = extract_regression(
        scenario_def=sd,
        shrunk_user_turns=("b",),
        failure_signature={},
        extraction=ext,
        regression_id="reg_dup",
    )
    assert second.status == "skipped_duplicate"


def test_shrink_remove_user_turns(tmp_path: Path) -> None:
    pytest.importorskip("agent_spec_kit.shrink_engine")
    from agent_spec_kit.fuzz_config import ShrinkConfig
    from agent_spec_kit.shrink import remove_user_turns
    from agent_spec_kit.shrink_engine import shrink_user_turns

    calls: list[tuple[str, ...]] = []

    async def verify_batch(cands: Sequence[tuple[str, ...]]) -> list[bool]:
        out: list[bool] = []
        for turns in cands:
            calls.append(turns)
            out.append(turns == ("keep",))
        return out

    cfg = ShrinkConfig(passes=(remove_user_turns(),), confirm_runs=1, min_reproductions=1)
    import asyncio

    shrunk, n = asyncio.run(
        shrink_user_turns(
            original=("noise", "keep"), shrinking=cfg, verify_batch=verify_batch
        )
    )
    assert shrunk == ("keep",)
    assert n >= 1


_FC_AST = FuzzConfig(
    strategy=behaviour_grammar((UserAction(name="ast", templates=("gen",)),)),
    seed=2,
)


def _load_scenario_module(path: Path) -> Any:
    name = f"_ek_extract_test_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_extract_ast_interleaved_user_message_fuzz_assert(tmp_path: Path) -> None:
    src = tmp_path / "orig.py"
    src.write_text(
        """
import agent_spec_kit as ek
import agent_spec_kit.match as m
from agent_spec_kit.fuzz.behaviour_grammar import behaviour_grammar
from agent_spec_kit.fuzz_config import FuzzConfig, UserAction

_UA = UserAction(name="ast", templates=("gen",),)
_FC = FuzzConfig(strategy=behaviour_grammar((_UA,)), seed=2)

def always_true(s, agent):
    return True

@ek.scenario(agent_fixture="agent", tags=("x",))
async def src_case(s, agent):
    (
        s.user_message("scripted")
        .fuzz_conversation(fuzz_config=_FC, trials=1, max_user_turns=1)
        .assert_that(always_true)
    )
""".strip(),
        encoding="utf-8",
    )
    mod = _load_scenario_module(src)
    sd = ScenarioDef(
        name="src_case",
        module=mod.__name__,
        fn=mod.src_case,
        agent_fixture="agent",
        user_fixture=None,
        repeats=1,
        tags=("x",),
        timeout_s=None,
        source=str(src),
        fixture_param_names=("agent",),
    )
    body_steps = (
        _UserMessageStep("scripted"),
        _FuzzConversationStep(fuzz_config=_FC_AST, trials=1, max_user_turns=1),
        _EnvAssertStep(fn=mod.always_true),
    )
    out = extract_regression(
        scenario_def=sd,
        failure_signature={},
        extraction=ExtractionConfig(target_file="regressions/out.py"),
        regression_id="reg_ast_1",
        body_steps=body_steps,
        concrete_per_generative_step={1: ("shrunk-line",)},
    )
    assert out.status == "written"
    target = src.parent / "regressions" / "out.py"
    text = target.read_text(encoding="utf-8")
    assert "import agent_spec_kit.match as m" in text
    assert "user_message(\"scripted\")" in text or "user_message('scripted')" in text
    assert "shrunk-line" in text
    assert "always_true" in text
    assert "fuzz_conversation" not in text


def test_extract_ast_simulate_replaced(tmp_path: Path) -> None:
    src = tmp_path / "sim.py"
    src.write_text(
        """
import agent_spec_kit as ek

def ok(s, agent):
    return True

@ek.scenario(agent_fixture="agent", tags=("s",))
async def sim_case(s, agent):
    (
        s.simulate_conversation(seed_actor="agent", seed_input="hi", max_turns=2)
        .assert_that(ok)
    )
""".strip(),
        encoding="utf-8",
    )
    mod = _load_scenario_module(src)
    sd = ScenarioDef(
        name="sim_case",
        module=mod.__name__,
        fn=mod.sim_case,
        agent_fixture="agent",
        user_fixture=None,
        repeats=1,
        tags=("s",),
        timeout_s=None,
        source=str(src),
        fixture_param_names=("agent",),
    )
    body_steps = (
        _SimulateStep(
            max_turns=2,
            stop_condition=None,
            stop_on_actor="any",
            seed_actor="agent",
            seed_input="hi",
        ),
        _EnvAssertStep(fn=mod.ok),
    )
    out = extract_regression(
        scenario_def=sd,
        failure_signature={},
        extraction=ExtractionConfig(target_file="regressions/sim_out.py"),
        regression_id="reg_sim_1",
        body_steps=body_steps,
        concrete_per_generative_step={0: ("u1", "u2")},
    )
    assert out.status == "written"
    text = (src.parent / "regressions" / "sim_out.py").read_text(encoding="utf-8")
    assert "u1" in text and "u2" in text
    assert "simulate_conversation" not in text


def test_extract_ast_action_lambda_is_partial(tmp_path: Path) -> None:
    src = tmp_path / "lam.py"
    src.write_text(
        """
import agent_spec_kit as ek

@ek.scenario(agent_fixture="agent", tags=("l",))
async def lam_case(s, agent):
    (s.action(lambda s, agent: None).user_message("z"))
""".strip(),
        encoding="utf-8",
    )
    mod = _load_scenario_module(src)
    sd = ScenarioDef(
        name="lam_case",
        module=mod.__name__,
        fn=mod.lam_case,
        agent_fixture="agent",
        user_fixture=None,
        repeats=1,
        tags=("l",),
        timeout_s=None,
        source=str(src),
        fixture_param_names=("agent",),
    )
    body_steps = (
        _ActionStep(fn=lambda s, agent: None),
        _UserMessageStep("z"),
    )
    out = extract_regression(
        scenario_def=sd,
        failure_signature={},
        extraction=ExtractionConfig(target_file="regressions/lam_out.py"),
        regression_id="reg_lam_1",
        body_steps=body_steps,
        concrete_per_generative_step={},
    )
    assert out.status == "partial"
    text = (src.parent / "regressions" / "lam_out.py").read_text(encoding="utf-8")
    assert "TODO" in text


def test_extract_ast_ignores_docstring_expression(tmp_path: Path) -> None:
    src = tmp_path / "doc.py"
    src.write_text(
        """
import agent_spec_kit as ek

def ok(s, agent):
    return True

@ek.scenario(agent_fixture="agent", tags=("d",))
async def doc_case(s, agent):
    "has leading docstring expression"
    (s.user_message("x").assert_that(ok))
""".strip(),
        encoding="utf-8",
    )
    mod = _load_scenario_module(src)
    sd = ScenarioDef(
        name="doc_case",
        module=mod.__name__,
        fn=mod.doc_case,
        agent_fixture="agent",
        user_fixture=None,
        repeats=1,
        tags=("d",),
        timeout_s=None,
        source=str(src),
        fixture_param_names=("agent",),
    )
    body_steps = (
        _UserMessageStep("x"),
        _EnvAssertStep(fn=mod.ok),
    )
    out = extract_regression(
        scenario_def=sd,
        failure_signature={},
        extraction=ExtractionConfig(target_file="regressions/doc_out.py"),
        regression_id="reg_doc_1",
        body_steps=body_steps,
        concrete_per_generative_step={},
    )
    assert out.status == "written"


def test_extract_ast_ignores_mid_materialise_and_continues_chain(tmp_path: Path) -> None:
    src = tmp_path / "mid_materialise.py"
    src.write_text(
        """
import agent_spec_kit as ek

def ok(s, agent):
    return True

@ek.scenario(agent_fixture="agent", tags=("mm",))
async def mm_case(s, agent):
    s.user_message("seed")
    await s.materialise()
    (s.simulate_conversation(seed_actor="agent", seed_input="hello", max_turns=2).assert_that(ok))
""".strip(),
        encoding="utf-8",
    )
    mod = _load_scenario_module(src)
    sd = ScenarioDef(
        name="mm_case",
        module=mod.__name__,
        fn=mod.mm_case,
        agent_fixture="agent",
        user_fixture=None,
        repeats=1,
        tags=("mm",),
        timeout_s=None,
        source=str(src),
        fixture_param_names=("agent",),
    )
    body_steps = (
        _UserMessageStep("seed"),
        _SimulateStep(
            max_turns=2,
            stop_condition=None,
            stop_on_actor="any",
            seed_actor="agent",
            seed_input="hello",
        ),
        _EnvAssertStep(fn=mod.ok),
    )
    out = extract_regression(
        scenario_def=sd,
        failure_signature={},
        extraction=ExtractionConfig(target_file="regressions/mm_out.py"),
        regression_id="reg_mm_1",
        body_steps=body_steps,
        concrete_per_generative_step={1: ("u1",)},
    )
    assert out.status == "written"
    text = (src.parent / "regressions" / "mm_out.py").read_text(encoding="utf-8")
    assert "simulate_conversation" not in text
    assert "u1" in text
    assert "\n        .assert_that(ok)" in text


def test_extract_ast_skip_duplicate_by_fingerprint(tmp_path: Path) -> None:
    src = tmp_path / "dup_fp.py"
    src.write_text(
        """
import agent_spec_kit as ek

def ok(s, agent):
    return True

@ek.scenario(agent_fixture="agent", tags=("d",))
async def dup_case(s, agent):
    (s.user_message("seed").assert_that(ok))
""".strip(),
        encoding="utf-8",
    )
    mod = _load_scenario_module(src)
    sd = ScenarioDef(
        name="dup_case",
        module=mod.__name__,
        fn=mod.dup_case,
        agent_fixture="agent",
        user_fixture=None,
        repeats=1,
        tags=("d",),
        timeout_s=None,
        source=str(src),
        fixture_param_names=("agent",),
    )
    body_steps = (_UserMessageStep("seed"), _EnvAssertStep(fn=mod.ok))
    ext = ExtractionConfig(target_file="regressions/dup_out.py", duplicate_policy="skip")
    first = extract_regression(
        scenario_def=sd,
        failure_signature={},
        extraction=ext,
        regression_id="reg_fp_1",
        body_steps=body_steps,
        concrete_per_generative_step={},
    )
    second = extract_regression(
        scenario_def=sd,
        failure_signature={},
        extraction=ext,
        regression_id="reg_fp_2",
        body_steps=body_steps,
        concrete_per_generative_step={},
    )
    assert first.status == "written"
    assert second.status == "skipped_duplicate"
