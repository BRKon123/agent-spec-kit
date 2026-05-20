#!/usr/bin/env python3
"""Run each framework's check against fail traces; write failures_samples.yaml."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import traceback
from pathlib import Path
from typing import Any

import yaml

_EXPR = Path(__file__).resolve().parents[1]
if str(_EXPR) not in sys.path:
    sys.path.insert(0, str(_EXPR))

from shared.paths import ensure_paths

ensure_paths()

import agent_spec_kit.match as m
from agent_spec_kit.match.api import check
from agent_spec_kit.match.types import path_to_str

from catalog import FAILURE_SPECIFICITY, FAILURE_SPECIFICITY_GRADES, SPECIMENS
from implementations.braintrust.scorers import SCORERS
from implementations.langsmith.evaluators import EVALUATORS as LS_EVALUATORS
from implementations.pydantic_evals.evaluators import EVALUATORS as PE_EVALUATORS
from shared.ask_specs import output_spec, tools_spec
from shared.canonical_checks import CHECK_BY_ID
from shared.fail_traces import fail_trace_for
from shared.trace_helpers import walk_root_tools
from shared.trace_io import load_trace, save_trace

_TELECOM = _EXPR.parent / "telecom_support"
if str(_TELECOM) not in sys.path:
    sys.path.insert(0, str(_TELECOM))

from specimens.messages import meta  # noqa: E402
from shared.store_sim import insert_ticket  # noqa: E402
from store.seeds import apply_seed  # noqa: E402
from store.store import TelcoStore  # noqa: E402
from tasks.specs import oracles as o  # noqa: E402

CHECK_IDS = [s.check_id for s in SPECIMENS]
FRAMEWORKS = [
    "agent_spec_kit",
    "pytest_plain",
    "langsmith",
    "pydantic_evals",
    "promptfoo",
    "braintrust",
]

FAIL_DIR = _EXPR / "traces_fail"


def _truncate(msg: str, limit: int = 400) -> str:
    msg = " ".join(msg.split())
    return msg if len(msg) <= limit else msg[: limit - 3] + "..."


def _format_ask_errors(errors: tuple) -> str:
    parts: list[str] = []
    for err in errors[:3]:
        parts.append(
            f"path={path_to_str(err.path)} code={err.code} "
            f"expected={err.expected!r} actual={err.actual!r} ({err.message})"
        )
    return _truncate(" | ".join(parts))


def _c11_oracle_fail_message() -> str:
    base = Path(tempfile.mkdtemp(prefix="fail_c11_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, "task_T04")
        try:
            o.assert_ticket_exists(telco)
            return "unexpected pass"
        except AssertionError as exc:
            return _truncate(str(exc))
    finally:
        shutil.rmtree(base, ignore_errors=True)


PYTEST_TEST_FN = {
    "C01": "test_c01_output_rubric",
    "C02": "test_c02_object_shape",
    "C03": "test_c03_conditional_object",
    "C04": "test_c04_numeric_regex",
    "C05": "test_c05_ordered_sequence",
    "C06": "test_c06_forbidden_tools",
    "C07": "test_c07_tool_args",
    "C08": "test_c08_tool_result",
    "C09": "test_c09_nested_tools",
    "C10": "test_c10_unordered_siblings",
    "C11": "test_c11_db_state",
    "C12": "test_c12_multi_turn_memory",
}


def _run_pytest_check(check_id: str, trace: dict[str, Any]) -> str:
    from shared import pytest_checks as pc

    if check_id == "C11" or trace.get("_fail_mode") == "c11_no_ticket":
        try:
            pc._c11_fail_no_ticket(trace)
            return "unexpected pass"
        except AssertionError as exc:
            return _truncate(str(exc))

    try:
        pc.run_check(check_id, trace)
        return "unexpected pass"
    except AssertionError as exc:
        msg = str(exc) or (exc.args[0] if exc.args else "AssertionError")
        return _truncate(msg if isinstance(msg, str) else repr(msg))


def _run_ask(check_id: str, trace: dict[str, Any]) -> str:
    if check_id == "C11" or trace.get("_fail_mode") == "c11_no_ticket":
        return _c11_oracle_fail_message()

    if check_id == "C01":
        spec = output_spec("C01")
        actual = trace.get("output", "")
    else:
        spec = tools_spec(check_id)
        if check_id == "C06":
            from agent_spec_kit.match.api import forbidden_tool_calls_matcher

            actual = walk_root_tools(trace)
            fspec = forbidden_tool_calls_matcher(
                [m.tool_call("apply_bill_credit")], ordered=True
            )
            r = check(fspec, actual)
            if r.ok:
                return "unexpected pass"
            return _format_ask_errors(r.errors)
        if check_id == "C12":
            turns = trace.get("turns") or []
            actual = walk_root_tools(turns[-1]) if turns else []
        else:
            actual = walk_root_tools(trace)
    if spec is None:
        return "no ask spec"
    r = check(spec, actual)
    if r.ok:
        return "unexpected pass"
    return _format_ask_errors(r.errors)


def _run_langsmith(check_id: str, trace: dict[str, Any]) -> str:
    if check_id == "C11":
        return _c11_oracle_fail_message()
    r = LS_EVALUATORS[check_id](trace)
    if r.get("score") == 1:
        return "unexpected pass"
    return _truncate(str(r))


def _run_pydantic(check_id: str, trace: dict[str, Any]) -> str:
    return _run_pytest_check(check_id, trace)


def _run_braintrust(check_id: str, trace: dict[str, Any]) -> str:
    if check_id == "C11":
        return _truncate(str({"key": "c11", "score": 0, "note": _c11_oracle_fail_message()}))
    r = SCORERS[check_id](trace)
    if r.get("score") == 1:
        return "unexpected pass"
    return _truncate(str(r))


def _run_promptfoo(check_id: str, trace: dict[str, Any]) -> str:
    if check_id == "C11":
        try:
            msg = _c11_oracle_fail_message()
            return msg if msg != "unexpected pass" else "unexpected pass"
        except Exception as exc:
            return _truncate(f"{type(exc).__name__}: {exc}")

    mod_name = f"assert_{check_id.lower()}"
    path = _EXPR / "implementations" / "promptfoo" / f"{mod_name}.py"
    import importlib.util

    spec = importlib.util.spec_from_file_location(mod_name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    out = json.dumps(trace)
    result = mod.get_assert(out, {"vars": {"check_id": check_id}})
    if result is True or result == 1:
        return "unexpected pass"
    if isinstance(result, dict):
        return _truncate(str(result))
    return f"assertion returned {result!r}"


# Fixed exemplar strings (from MANUAL_FAILURE_CLASSIFICATION.md captures).
GRADE_EXEMPLARS: dict[str, str] = {
    "A": "path=$[1] code=missing_element expected=... actual=... (tool/field witness)",
    "B": "get_line_status.args.line_id expected 'LINE-001', got 'LINE-002'  OR  {'key': 'tool_args', 'score': 0}",
    "C": "(no pure C-grade capture in this harness)",
    "D": "AssertionError  OR  assertion returned False",
    "E": "(no E-grade capture in this harness)",
}


def main() -> None:
    FAIL_DIR.mkdir(parents=True, exist_ok=True)
    samples: dict[str, Any] = {
        "_meta": {
            "description": "Captured fail-trace messages per framework (see scripts/collect_failure_samples.py)",
            "grade_rubric": "A=path+expected/actual B=rule/tool slice C=step index D=generic E=opaque",
        },
        "grade_exemplars": dict(GRADE_EXEMPLARS),
        "classification_source": "MANUAL_FAILURE_CLASSIFICATION.md (not auto-classified)",
    }

    runners = {
        "agent_spec_kit": _run_ask,
        "pytest_plain": _run_pytest_check,
        "langsmith": _run_langsmith,
        "pydantic_evals": _run_pydantic,
        "promptfoo": _run_promptfoo,
        "braintrust": _run_braintrust,
    }

    for cid in CHECK_IDS:
        fail = fail_trace_for(cid)
        if fail.get("_fail_mode") != "c11_no_ticket":
            save_trace(cid, fail, directory=FAIL_DIR)
        assert CHECK_BY_ID[cid](load_trace(cid)), f"golden should pass {cid}"
        if cid != "C11":
            assert not CHECK_BY_ID[cid](fail), f"fail trace should not pass {cid}"

        block: dict[str, str] = {}
        for fw, run in runners.items():
            try:
                msg = run(cid, fail)
            except Exception as exc:
                msg = _truncate(f"{type(exc).__name__}: {exc}")
            block[fw] = msg
        grades = FAILURE_SPECIFICITY[cid]
        block["_grades"] = "/".join(grades[fw] for fw in FRAMEWORKS)
        samples[cid] = block

    out = _EXPR / "failures_samples.yaml"
    out.write_text(
        yaml.safe_dump(samples, sort_keys=False, allow_unicode=True, width=120),
        encoding="utf-8",
    )
    print(f"wrote {out}")

    # Write human-readable report
    report = _EXPR / "FAILURE_SAMPLES.md"
    rep_lines = [
        "# Failure message samples (fail traces)",
        "",
        "Generated by `scripts/collect_failure_samples.py`. Fail traces in `traces_fail/`.",
        "Grades from [`MANUAL_FAILURE_CLASSIFICATION.md`](../MANUAL_FAILURE_CLASSIFICATION.md) (`catalog.py`).",
        "",
        "## Grade exemplars (what A–E look like in this harness)",
        "",
        "| Grade | Typical shape in our captures |",
        "| --- | --- |",
    ]
    for g, ex in samples["grade_exemplars"].items():
        rep_lines.append(f"| **{g}** | `{ex}` |")
    rep_lines.extend(["", "## Per-check captures", ""])
    for cid in CHECK_IDS:
        rep_lines.append(f"### {cid}")
        rep_lines.append(f"Grades (ask/py/ls/pe/pf/bt): `{samples[cid]['_grades']}`")
        rep_lines.append("")
        for fw in FRAMEWORKS:
            rep_lines.append(f"- **{fw}**: `{samples[cid][fw]}`")
        rep_lines.append("")
    report.write_text("\n".join(rep_lines) + "\n", encoding="utf-8")
    print(f"wrote {report}")


if __name__ == "__main__":
    main()
