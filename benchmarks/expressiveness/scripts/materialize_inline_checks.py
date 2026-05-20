#!/usr/bin/env python3
"""Emit framework implementations with canonical check bodies inlined in CHECK regions."""

from __future__ import annotations

import inspect
import re
import textwrap
from pathlib import Path

_EXPR = Path(__file__).resolve().parents[1]
import sys

if str(_EXPR) not in sys.path:
    sys.path.insert(0, str(_EXPR))

from shared.paths import ensure_paths

ensure_paths()

from shared import canonical_checks as cc

CHECK_FUNCS: list[tuple[str, str, str]] = [
    ("C01", "c01", "check_c01_output_rubric"),
    ("C02", "c02", "check_c02_object_shape"),
    ("C03", "c03", "check_c03_conditional_object"),
    ("C04", "c04", "check_c04_numeric_regex"),
    ("C05", "c05", "check_c05_ordered_sequence"),
    ("C06", "c06", "check_c06_forbidden_tools"),
    ("C07", "c07", "check_c07_tool_args"),
    ("C08", "c08", "check_c08_tool_result"),
    ("C09", "c09", "check_c09_nested_tools"),
    ("C10", "c10", "check_c10_unordered_siblings"),
    ("C11", "c11", "check_c11_db_state"),
    ("C12", "c12", "check_c12_multi_turn_memory"),
]

LS_KEYS = {
    "C01": "output_rubric",
    "C02": "object_shape",
    "C03": "conditional_object",
    "C04": "numeric_regex",
    "C05": "ordered_sequence",
    "C06": "forbidden_tools",
    "C07": "tool_args",
    "C08": "tool_result",
    "C09": "nested_tools",
    "C10": "unordered_siblings",
    "C11": "db_state",
    "C12": "multi_turn_memory",
}


def _function_body(fn_name: str) -> str:
    src = inspect.getsource(getattr(cc, fn_name))
    body = textwrap.dedent("\n".join(src.splitlines()[1:]))
    return body.rstrip() + "\n"


def _indent(block: str, n: int = 4) -> str:
    return "".join(" " * n + line if line.strip() else line for line in block.splitlines(keepends=True))


def _pytest_return_to_assert(body: str) -> str:
    return _rewrite_returns(
        body,
        false_line="assert False",
        true_line="assert True",
        expr_line="assert EXPR",
        else_before_sibling_return=True,
    )


def _return_needs_multiline(stripped: str) -> bool:
    if not stripped.startswith("return "):
        return False
    expr = stripped[len("return ") :]
    return expr.count("(") > expr.count(")")


def _rewrite_returns(
    body: str,
    *,
    false_line: str,
    true_line: str,
    expr_line: str,
    else_before_sibling_return: bool = False,
) -> str:
    """Rewrite return statements; multiline returns become ``ok = ...`` + closing wrapper line."""
    out: list[str] = []
    pending_ok_close = False
    else_after_indent: int | None = None
    last_if_indent: int | None = None
    blockers_since_if = False
    for line in body.splitlines():
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        if pending_ok_close:
            out.append(line)
            if stripped == ")":
                out.append(expr_line.replace("EXPR", "ok"))
                pending_ok_close = False
            continue
        if stripped.startswith("if ") and stripped.endswith(":"):
            last_if_indent = indent
            blockers_since_if = False
        elif (
            last_if_indent is not None
            and indent == last_if_indent
            and not stripped.startswith("if ")
            and not stripped.startswith("return ")
        ):
            blockers_since_if = True
        if stripped == "return False":
            out.append(line.replace("return False", false_line))
        elif stripped == "return True":
            out.append(line.replace("return True", true_line))
        elif _return_needs_multiline(stripped):
            out.append(line.replace("return ", "ok = ", 1))
            pending_ok_close = True
            if (
                else_before_sibling_return
                and not blockers_since_if
                and last_if_indent is not None
                and indent == last_if_indent + 4
            ):
                else_after_indent = last_if_indent
        elif stripped.startswith("return "):
            expr = stripped[len("return ") :]
            if (
                else_before_sibling_return
                and not blockers_since_if
                and else_after_indent == indent
            ):
                out.append(" " * indent + "else:")
                else_after_indent = None
                converted = expr_line.replace("EXPR", expr)
                out.append(" " * (indent + 4) + converted.lstrip())
            else:
                out.append(line.replace(stripped, expr_line.replace("EXPR", expr)))
            if (
                else_before_sibling_return
                and not blockers_since_if
                and last_if_indent is not None
                and indent == last_if_indent + 4
            ):
                else_after_indent = last_if_indent
        else:
            out.append(line)
    return "\n".join(out) + "\n"


def _langsmith_return_to_score(body: str, score_key: str) -> str:
    return _rewrite_returns(
        body,
        false_line=f'return _score(False, "{score_key}")',
        true_line=f'return _score(True, "{score_key}")',
        expr_line=f'return _score(EXPR, "{score_key}")',
    )


def _plain_return_ok(body: str) -> str:
    """For pydantic/braintrust/promptfoo: keep return bool inside CHECK."""
    return body


COMMON_IMPORTS = '''from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

_EXPR = Path(__file__).resolve().parents[2]
if str(_EXPR) not in sys.path:
    sys.path.insert(0, str(_EXPR))

from shared.paths import ensure_paths

ensure_paths()

from specimens.messages import meta
from shared.store_sim import insert_ticket
from shared.trace_helpers import (
    any_forbidden_present,
    find_tool,
    nested_children,
    ordered_subsequence,
    tool_names,
    unordered_set,
    walk_root_tools,
)

_TELECOM = _EXPR.parent / "telecom_support"
if str(_TELECOM) not in sys.path:
    sys.path.insert(0, str(_TELECOM))

from store.seeds import apply_seed  # noqa: E402
from store.store import TelcoStore  # noqa: E402
from tasks.specs import oracles as o  # noqa: E402
'''


def emit_pytest() -> str:
    parts = [
        '"""Plain pytest — inlined check logic in CHECK regions (LOC benchmark)."""',
        "",
        COMMON_IMPORTS,
        "from shared.trace_io import load_trace",
        "",
    ]
    for cid, slug, fn in CHECK_FUNCS:
        body = _function_body(fn)
        # module-level constants used by some checks
        extra = ""
        if fn == "check_c02_object_shape":
            extra = (
                "_C02_REQUIRED_KEYS = frozenset("
                '{"severity", "recommended_action", "escalation_reason"})\n\n'
            )
        if fn == "check_c08_tool_result":
            extra = (
                '_C08_REQUIRED_KEYS = frozenset({"severity", "recommended_action", "summary"})\n\n'
            )
        parts.append(f"def test_{slug}_object_shape():" if slug == "c02" else f"def test_{slug}_{fn.split('_', 2)[-1]}():")
        # fix test names
    # rebuild with correct test names
    parts = [
        '"""Plain pytest — inlined check logic in CHECK regions (LOC benchmark)."""',
        "",
        COMMON_IMPORTS,
        "from shared.trace_io import load_trace",
        "",
        '_C02_REQUIRED_KEYS = frozenset({"severity", "recommended_action", "escalation_reason"})',
        '_C08_REQUIRED_KEYS = frozenset({"severity", "recommended_action", "summary"})',
        "",
    ]
    name_map = {
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
    for cid, _slug, fn in CHECK_FUNCS:
        body = _pytest_return_to_assert(_function_body(fn))
        parts.append(f"def {name_map[cid]}():")
        parts.append(f'    trace = load_trace("{cid}")')
        parts.append("    # CHECK_START")
        parts.extend(_indent(body, 4).splitlines())
        parts.append("    # CHECK_END")
        parts.append("")
    return "\n".join(parts) + "\n"


def emit_langsmith() -> str:
    parts = [
        '"""LangSmith-style evaluators — inlined check logic in CHECK regions."""',
        "",
        COMMON_IMPORTS,
        "from shared.trace_io import load_trace",
        "",
        '_C02_REQUIRED_KEYS = frozenset({"severity", "recommended_action", "escalation_reason"})',
        '_C08_REQUIRED_KEYS = frozenset({"severity", "recommended_action", "summary"})',
        "",
        "def _score(ok: bool, key: str) -> dict[str, Any]:",
        '    return {"key": key, "score": 1 if ok else 0}',
        "",
    ]
    eval_names = {
        "C01": "eval_c01_output_rubric",
        "C02": "eval_c02_object_shape",
        "C03": "eval_c03_conditional_object",
        "C04": "eval_c04_numeric_regex",
        "C05": "eval_c05_ordered_sequence",
        "C06": "eval_c06_forbidden",
        "C07": "eval_c07_tool_args",
        "C08": "eval_c08_tool_result",
        "C09": "eval_c09_nested",
        "C10": "eval_c10_unordered",
        "C11": "eval_c11_db_state",
        "C12": "eval_c12_multi_turn_memory",
    }
    for cid, _slug, fn in CHECK_FUNCS:
        body = _langsmith_return_to_score(_function_body(fn), LS_KEYS[cid])
        parts.append(
            f"def {eval_names[cid]}(outputs: dict[str, Any], reference_outputs: dict | None = None) -> dict:"
        )
        parts.append("    trace = outputs")
        parts.append("    # CHECK_START")
        parts.extend(_indent(body, 4).splitlines())
        parts.append("    # CHECK_END")
        parts.append("")
    parts.append("EVALUATORS: dict[str, Any] = {")
    for cid, _slug, _fn in CHECK_FUNCS:
        parts.append(f'    "{cid}": {eval_names[cid]},')
    parts.append("}")
    parts.append("")
    parts.append("def run_evaluator(check_id: str, outputs: dict[str, Any] | None = None) -> dict:")
    parts.append("    data = outputs if outputs is not None else load_trace(check_id)")
    parts.append("    return EVALUATORS[check_id](data)")
    parts.append("")
    return "\n".join(parts) + "\n"


def emit_pydantic() -> str:
    pe_names = {
        "C01": ("eval_c01_output_rubric", "output_rubric"),
        "C02": ("eval_c02_validate_shape", "object_shape"),
        "C03": ("eval_c03_conditional", "conditional"),
        "C04": ("eval_c04_numeric", "numeric"),
        "C05": ("eval_c05_span_sequence", "sequence"),
        "C06": ("eval_c06_forbid_span", "forbid"),
        "C07": ("eval_c07_tool_args", "tool_args"),
        "C08": ("eval_c08_tool_result", "tool_result"),
        "C09": ("eval_c09_nested", "nested"),
        "C10": ("eval_c10_unordered", "unordered"),
        "C11": ("eval_c11_db_state", "db_state"),
        "C12": ("eval_c12_multi_turn", "multi_turn"),
    }
    parts = [
        '"""Pydantic Evals-style evaluators — inlined check logic in CHECK regions."""',
        "",
        COMMON_IMPORTS.replace("from typing import Any", ""),
        "from collections.abc import Callable",
        "",
        "from shared.trace_io import load_trace",
        "",
        '_C02_REQUIRED_KEYS = frozenset({"severity", "recommended_action", "escalation_reason"})',
        '_C08_REQUIRED_KEYS = frozenset({"severity", "recommended_action", "summary"})',
        "",
    ]
    for cid, _slug, fn in CHECK_FUNCS:
        body = _plain_return_ok(_function_body(fn))
        ename = pe_names[cid][0]
        parts.append(f'def {ename}(check_id: str = "{cid}") -> bool:')
        parts.append(f"    trace = load_trace(check_id)")
        parts.append("    # CHECK_START")
        parts.extend(_indent(body, 4).splitlines())
        parts.append("    # CHECK_END")
        parts.append("")
    parts.append("EVALUATORS: dict[str, Callable[[str], bool]] = {")
    for cid, _slug, _fn in CHECK_FUNCS:
        parts.append(f'    "{cid}": {pe_names[cid][0]},')
    parts.append("}")
    parts.append("")
    return "\n".join(parts) + "\n"


def _braintrust_return_to_wrap(body: str, cid: str) -> str:
    return _rewrite_returns(
        body,
        false_line=f'return _wrap(False, "{cid}")',
        true_line=f'return _wrap(True, "{cid}")',
        expr_line=f'return _wrap(EXPR, "{cid}")',
    )


def emit_braintrust() -> str:
    parts = [
        '"""Braintrust-style scorers — inlined check logic in CHECK regions."""',
        "",
        COMMON_IMPORTS,
        "",
        '_C02_REQUIRED_KEYS = frozenset({"severity", "recommended_action", "escalation_reason"})',
        '_C08_REQUIRED_KEYS = frozenset({"severity", "recommended_action", "summary"})',
        "",
        "def _wrap(ok: bool, check_id: str) -> dict[str, Any]:",
        '    return {"key": check_id.lower(), "score": 1 if ok else 0}',
        "",
    ]
    for cid, slug, fn in CHECK_FUNCS:
        body = _braintrust_return_to_wrap(_function_body(fn), cid)
        parts.append(f"def score_{slug}(output: dict[str, Any], expected: dict[str, Any] | None = None) -> dict:")
        parts.append("    trace = output")
        parts.append("    # CHECK_START")
        parts.extend(_indent(body, 4).splitlines())
        parts.append("    # CHECK_END")
        parts.append("")
    parts.append("SCORERS: dict[str, Any] = {")
    for cid, slug, _fn in CHECK_FUNCS:
        parts.append(f'    "{cid}": score_{slug},')
    parts.append("}")
    parts.append("")
    return "\n".join(parts) + "\n"


def emit_promptfoo_assert(cid: str, fn: str) -> str:
    body = _plain_return_ok(_function_body(fn))
    imports = COMMON_IMPORTS
    return (
        f'"""Promptfoo assertion for {cid} — inlined check logic."""\n\n'
        f"{imports}\n"
        "import json\n\n"
        "def get_assert(output: str, context: dict) -> bool | float | dict:\n"
        "    trace = json.loads(output)\n"
        "    # CHECK_START\n"
        f"{_indent(body, 4)}"
        "    # CHECK_END\n"
    )


def emit_promptfoo_yaml() -> str:
    lines = [
        "# Expressiveness benchmark — per-specimen assertions with inlined check logic.",
        "# Run: npx promptfoo@latest eval -c benchmarks/expressiveness/implementations/promptfoo",
        "",
        "description: Expressiveness specimens (inlined oracle LOC)",
        "",
        "providers:",
        "  - id: file://./provider.py",
        "",
        "prompts:",
        '  - "{{check_id}}"',
        "",
        "tests:",
    ]
    for cid, slug, _fn in CHECK_FUNCS:
        lines.append(f"  - vars: {{check_id: {cid}}}")
        lines.append("    assert:")
        lines.append("      - type: python")
        lines.append(f"        value: file://./assert_{slug}.py")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    impl = _EXPR / "implementations"
    (impl / "pytest_plain" / "test_canonical_checks.py").write_text(emit_pytest(), encoding="utf-8")
    (impl / "langsmith" / "evaluators.py").write_text(emit_langsmith(), encoding="utf-8")
    (impl / "pydantic_evals" / "evaluators.py").write_text(emit_pydantic(), encoding="utf-8")
    (impl / "braintrust" / "scorers.py").write_text(emit_braintrust(), encoding="utf-8")

    pf = impl / "promptfoo"
    for old in pf.glob("assert_*.py"):
        old.unlink()
    for cid, slug, fn in CHECK_FUNCS:
        (pf / f"assert_{slug}.py").write_text(emit_promptfoo_assert(cid, fn), encoding="utf-8")
    (pf / "promptfooconfig.yaml").write_text(emit_promptfoo_yaml(), encoding="utf-8")
    if (pf / "assert_canonical.py").is_file():
        (pf / "assert_canonical.py").unlink()

    print("materialized inline checks for pytest, langsmith, pydantic_evals, braintrust, promptfoo")


if __name__ == "__main__":
    main()
