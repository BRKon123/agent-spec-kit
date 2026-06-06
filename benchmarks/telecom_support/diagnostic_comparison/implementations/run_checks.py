"""Dispatch to hand-written per-scenario framework modules."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import Any

_BENCH = Path(__file__).resolve().parents[2]
if str(_BENCH) not in sys.path:
    sys.path.insert(0, str(_BENCH))

from scripts.diagnostic_quality_lib import FailureWitness

_TRUNC = 4000
_FRAMEWORK_DIRS = ("pytest_plain", "langsmith", "pydantic_evals", "promptfoo", "braintrust", "deepeval", "ragas")


class EvalFailed(Exception):
    """Scenario eval failed; message is the native framework failure text."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _truncate(msg: str) -> str:
    msg = msg.strip()
    if len(msg) <= _TRUNC:
        return msg
    return msg[: _TRUNC - 3] + "..."


def _module_name(family: str, task: str) -> str:
    return f"F{int(family[1:]):02d}_{task}"


def _load_slot_module(framework: str, family: str, task: str):
    if framework not in _FRAMEWORK_DIRS:
        raise KeyError(f"unknown framework: {framework}")
    mod_name = _module_name(family, task)
    return importlib.import_module(
        f"diagnostic_comparison.implementations.{framework}.{mod_name}"
    )


def _capture_pytest_plain(mod: Any, artifact: dict[str, Any], witness: FailureWitness) -> str:
    try:
        mod.evaluate(artifact, witness)
    except AssertionError as exc:
        msg = str(exc).strip() or "AssertionError"
        return _truncate(msg if msg.startswith("Assertion") else f"AssertionError: {msg}")
    except EvalFailed as exc:
        return _truncate(exc.message)
    return "unexpected pass"


def _capture_langsmith(mod: Any, artifact: dict[str, Any], witness: FailureWitness) -> str:
    try:
        result = mod.evaluate(artifact, witness)
    except EvalFailed as exc:
        return _truncate(exc.message)
    if isinstance(result, dict) and result.get("score") == 1:
        return "unexpected pass"
    return _truncate(str(result))


def _capture_pydantic_evals(mod: Any, artifact: dict[str, Any], witness: FailureWitness) -> str:
    try:
        mod.evaluate(artifact, witness)
    except AssertionError as exc:
        msg = str(exc).strip() or "AssertionError"
        return _truncate(msg if msg.startswith("Assertion") else f"AssertionError: {msg}")
    except EvalFailed as exc:
        return _truncate(exc.message)
    return "unexpected pass"


def _capture_promptfoo(mod: Any, artifact: dict[str, Any], witness: FailureWitness) -> str:
    output = json.dumps(artifact, default=str)
    context = {"vars": {"family": artifact.get("family"), "task": artifact.get("task")}}
    try:
        result = mod.get_assert(output, context)
    except EvalFailed as exc:
        return _truncate(exc.message)
    if result is True or result == 1:
        return "unexpected pass"
    if isinstance(result, dict):
        return _truncate(str(result))
    return _truncate(f"assertion returned {result!r}")


def _capture_braintrust(mod: Any, artifact: dict[str, Any], witness: FailureWitness) -> str:
    try:
        result = mod.score(artifact, witness)
    except EvalFailed as exc:
        return _truncate(exc.message)
    if isinstance(result, dict) and result.get("score") == 1:
        return "unexpected pass"
    return _truncate(str(result))


def _capture_deepeval(mod: Any, artifact: dict[str, Any], witness: FailureWitness) -> str:
    try:
        result = mod.evaluate(artifact, witness)
    except EvalFailed as exc:
        return _truncate(exc.message)
    if isinstance(result, dict) and result.get("score") == 1:
        return "unexpected pass"
    if isinstance(result, dict):
        comment = result.get("comment") or result.get("message")
        if comment:
            return _truncate(str(comment))
    return _truncate(str(result))


def _capture_ragas(mod: Any, artifact: dict[str, Any], witness: FailureWitness) -> str:
    try:
        result = mod.evaluate(artifact, witness)
    except EvalFailed as exc:
        return _truncate(exc.message)
    if isinstance(result, dict) and result.get("score") == 1:
        return "unexpected pass"
    if isinstance(result, dict):
        comment = result.get("comment") or result.get("message")
        if comment:
            return _truncate(str(comment))
    return _truncate(str(result))


def run_native_check(
    framework: str,
    artifact: dict[str, Any],
    witness: FailureWitness,
) -> str:
    mod = _load_slot_module(framework, artifact["family"], artifact["task"])
    if framework == "pytest_plain":
        return _capture_pytest_plain(mod, artifact, witness)
    if framework == "langsmith":
        return _capture_langsmith(mod, artifact, witness)
    if framework == "pydantic_evals":
        return _capture_pydantic_evals(mod, artifact, witness)
    if framework == "promptfoo":
        return _capture_promptfoo(mod, artifact, witness)
    if framework == "braintrust":
        return _capture_braintrust(mod, artifact, witness)
    if framework == "deepeval":
        return _capture_deepeval(mod, artifact, witness)
    if framework == "ragas":
        return _capture_ragas(mod, artifact, witness)
    raise KeyError(f"unknown framework: {framework}")


def framework_loc(framework: str, family: str, task: str) -> int:
    try:
        path = Path(__file__).parent / framework / f"{_module_name(family, task)}.py"
        if not path.is_file():
            return 0
        return len([ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()])
    except OSError:
        return 0


def run_pytest_plain(artifact: dict[str, Any], witness: FailureWitness) -> str:
    return run_native_check("pytest_plain", artifact, witness)


def run_langsmith(artifact: dict[str, Any], witness: FailureWitness) -> str:
    return run_native_check("langsmith", artifact, witness)


def run_pydantic_evals(artifact: dict[str, Any], witness: FailureWitness) -> str:
    return run_native_check("pydantic_evals", artifact, witness)


def run_promptfoo(artifact: dict[str, Any], witness: FailureWitness) -> str:
    return run_native_check("promptfoo", artifact, witness)


def run_braintrust(artifact: dict[str, Any], witness: FailureWitness) -> str:
    return run_native_check("braintrust", artifact, witness)
