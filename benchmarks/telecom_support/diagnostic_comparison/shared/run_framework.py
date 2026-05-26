"""Produce per-framework failure box text from a parsed FailureWitness."""

from __future__ import annotations

import re
from typing import Any

from scripts.diagnostic_quality_lib import FailureWitness, FRAMEWORKS

_TRUNC = 4000


def _truncate(msg: str) -> str:
    msg = msg.strip()
    if len(msg) <= _TRUNC:
        return msg
    return msg[: _TRUNC - 3] + "..."


def _evaluator_key(witness: FailureWitness) -> str:
    check = witness.check or "check"
    if check == "assert_tool_calls":
        return "tool_sequence"
    if check == "assert_that":
        return "state_oracle"
    if check == "assert_output":
        return "output_rubric"
    if check == "forbid_tool_calls":
        return "forbidden_tools"
    return check.replace("assert_", "")


def format_pytest_plain(witness: FailureWitness) -> str:
    # CHECK_START
    if witness.state_message:
        return _truncate(witness.state_message.replace("assert_that failed: ", ""))
    if witness.path and witness.expected and witness.actual:
        return _truncate(
            f"AssertionError: mismatch at {witness.path}"
        )
    if witness.headline:
        return _truncate("AssertionError")
    return "AssertionError"
    # CHECK_END


def format_langsmith(witness: FailureWitness) -> str:
    # CHECK_START
    key = _evaluator_key(witness)
    return _truncate(str({"key": key, "score": 0}))
    # CHECK_END


def format_pydantic_evals(witness: FailureWitness) -> str:
    return format_pytest_plain(witness)


def format_promptfoo(witness: FailureWitness) -> str:
    # CHECK_START
    return "assertion returned False"
    # CHECK_END


def format_braintrust(witness: FailureWitness) -> str:
    # CHECK_START
    key = _evaluator_key(witness)
    fam = witness.family.lower()
    return _truncate(str({"key": f"{fam}_{key}", "score": 0}))
    # CHECK_END


def format_agent_spec_kit(witness: FailureWitness) -> str:
    return _truncate(witness.panel_text or witness.headline)


_RUNNERS = {
    "agent_spec_kit": format_agent_spec_kit,
    "pytest_plain": format_pytest_plain,
    "langsmith": format_langsmith,
    "pydantic_evals": format_pydantic_evals,
    "promptfoo": format_promptfoo,
    "braintrust": format_braintrust,
}


def run_framework(framework: str, witness: FailureWitness) -> str:
    if framework not in _RUNNERS:
        raise KeyError(f"unknown framework: {framework}")
    return _RUNNERS[framework](witness)


def framework_loc(framework: str) -> int:
    """Non-comment lines in CHECK region for this framework's formatter."""
    import inspect

    fn = _RUNNERS.get(framework)
    if fn is None:
        return 0
    src = inspect.getsource(fn)
    lines = src.splitlines()
    in_block = False
    count = 0
    for line in lines:
        if "CHECK_START" in line:
            in_block = True
            continue
        if "CHECK_END" in line:
            break
        if in_block and line.strip() and not line.strip().startswith("#"):
            count += 1
    return count


def collect_all_framework_messages(witness: FailureWitness) -> dict[str, str]:
    return {fw: run_framework(fw, witness) for fw in FRAMEWORKS}
