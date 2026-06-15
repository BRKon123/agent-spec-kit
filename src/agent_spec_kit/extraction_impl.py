"""Implementation of regression extraction (AST / source append)."""

from __future__ import annotations

import ast
import hashlib
import importlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from agent_spec_kit.fuzz_config import ExtractionConfig
from agent_spec_kit.registries import ScenarioDef
from agent_spec_kit.scenario_core import (
    _FuzzConversationStep,
    _SimulateStep,
    _Step,
)


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    status: Literal["written", "skipped_duplicate", "errored", "noop", "partial"]
    regression_id: str | None
    message: str | None = None
    fingerprint: str | None = None
    function_name: str | None = None


def _target_path(scenario_def: ScenarioDef, extraction: ExtractionConfig) -> Path:
    base = Path(scenario_def.source).resolve().parent
    return (base / extraction.target_file).resolve()


def _fingerprint_for_turns(regression_id: str, turns: tuple[str, ...]) -> str:
    _ = regression_id
    payload = json.dumps({"turns": list(turns)}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:24]


def _fingerprint_concrete(regression_id: str, concrete: dict[int, tuple[str, ...]]) -> str:
    _ = regression_id
    payload = json.dumps(
        {
            "by_step": {str(k): list(v) for k, v in sorted(concrete.items())},
        },
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:24]


def _has_fingerprint(existing: str, fingerprint: str) -> bool:
    return f"fingerprint={fingerprint}" in existing


def _split_top_level_chain(expr: str) -> list[str]:
    parts: list[str] = []
    start = 0
    paren = bracket = brace = 0
    in_str: str | None = None
    escape = False
    i = 0
    n = len(expr)
    while i < n:
        ch = expr[i]
        if in_str is not None:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in ("'", '"'):
            in_str = ch
            i += 1
            continue
        if ch == "(":
            paren += 1
        elif ch == ")":
            paren = max(0, paren - 1)
        elif ch == "[":
            bracket += 1
        elif ch == "]":
            bracket = max(0, bracket - 1)
        elif ch == "{":
            brace += 1
        elif ch == "}":
            brace = max(0, brace - 1)
        elif ch == "." and paren == 0 and bracket == 0 and brace == 0:
            j = i + 1
            if j < n and (expr[j].isalpha() or expr[j] == "_"):
                while j < n and (expr[j].isalnum() or expr[j] == "_"):
                    j += 1
                if j < n and expr[j] == "(":
                    parts.append(expr[start:i])
                    start = i
        i += 1
    parts.append(expr[start:])
    return [p for p in parts if p]


def _prettify_unparsed_block_src(block_src: str) -> str:
    out_lines: list[str] = []
    for line in block_src.splitlines():
        stripped = line.strip()
        if line.startswith("    s.") and stripped.endswith(")") and "." in stripped:
            chain = _split_top_level_chain(stripped)
            if len(chain) > 1:
                out_lines.append("    (")
                out_lines.append(f"        {chain[0]}")
                for part in chain[1:]:
                    out_lines.append(f"        {part}")
                out_lines.append("    )")
                continue
        out_lines.append(line)
    return "\n".join(out_lines)


def _merge_import_block(existing: str, needed: str) -> str:
    if needed in existing:
        return existing
    lines = existing.splitlines()
    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith("import ") or line.startswith("from "):
            insert_at = i + 1
    lines.insert(insert_at, needed)
    return "\n".join(lines) + ("\n" if not existing.endswith("\n") else "")


def _unwrap_expr(stmt: ast.stmt) -> ast.expr | None:
    if not isinstance(stmt, ast.Expr):
        return None
    v = stmt.value
    if isinstance(v, ast.Tuple) and len(v.elts) == 1:
        return v.elts[0]
    return v


def _flatten_chain_calls(expr: ast.AST) -> list[ast.Call]:
    calls: list[ast.Call] = []

    def walk(node: ast.AST) -> None:
        if isinstance(node, ast.Call):
            walk(node.func)
            calls.append(node)
        elif isinstance(node, ast.Attribute):
            walk(node.value)
        elif isinstance(node, ast.Await):
            walk(node.value)

    walk(expr)
    return calls


def _chain_root_name(node: ast.AST) -> str | None:
    cur = node
    while isinstance(cur, (ast.Call, ast.Attribute)):
        if isinstance(cur, ast.Call):
            cur = cur.func
        else:
            cur = cur.value
    if isinstance(cur, ast.Name):
        return cur.id
    return None


def _is_materialise_call(call: ast.Call) -> bool:
    func = call.func
    if not isinstance(func, ast.Attribute):
        return False
    return func.attr == "materialise" and _chain_root_name(func) == "s"


def _is_docstring_expr(expr: ast.expr) -> bool:
    return isinstance(expr, ast.Constant) and isinstance(expr.value, str)


def _stmt_has_scenario_chain(st: ast.stmt) -> bool:
    expr = _unwrap_expr(st)
    if expr is None or _is_docstring_expr(expr):
        return False
    return any(
        not _is_materialise_call(c) and _chain_root_name(c.func) == "s"
        for c in _flatten_chain_calls(expr)
    )


def _collect_scenario_preamble(fn_node: ast.AsyncFunctionDef) -> list[ast.stmt]:
    """Statements before the main ``s.`` chain (e.g. bind_scenario_context, locals for asserts)."""
    preamble: list[ast.stmt] = []
    for st in fn_node.body:
        if _stmt_has_scenario_chain(st):
            break
        if isinstance(st, (ast.Assign, ast.AnnAssign)):
            preamble.append(st)
            continue
        if isinstance(st, ast.Expr):
            expr = _unwrap_expr(st)
            if expr is None or _is_docstring_expr(expr):
                continue
            if isinstance(expr, ast.Call) and _chain_root_name(expr) != "s":
                preamble.append(st)
    return preamble


def _collect_scenario_chain_calls(fn_node: ast.AsyncFunctionDef) -> list[ast.Call]:
    calls: list[ast.Call] = []
    for st in fn_node.body:
        expr = _unwrap_expr(st)
        if expr is None:
            continue
        if _is_docstring_expr(expr):
            continue
        calls.extend(_flatten_chain_calls(expr))
    return [
        c
        for c in calls
        if not _is_materialise_call(c) and _chain_root_name(c.func) == "s"
    ]


def _collect_load_names(node: ast.AST, *, skip: frozenset[str]) -> set[str]:
    out: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
            if child.id in skip:
                continue
            out.add(child.id)
    return out


def _rebase_call_chain(expr: ast.expr, call_tmpl: ast.Call) -> ast.Call:
    func = call_tmpl.func
    if not isinstance(func, ast.Attribute):
        msg = "expected Attribute call chain"
        raise TypeError(msg)
    new_func = ast.Attribute(value=expr, attr=func.attr, ctx=ast.Load())
    return ast.Call(func=new_func, args=call_tmpl.args, keywords=call_tmpl.keywords)


def _has_lambda(node: ast.AST) -> bool:
    return any(isinstance(x, ast.Lambda) for x in ast.walk(node))


def _leading_import_lines(source: str) -> str:
    lines = source.splitlines()
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped == "" or stripped.startswith("#"):
            continue
        if stripped.startswith("import ") or stripped.startswith("from "):
            out.append(line)
            continue
        break
    return "\n".join(out) + ("\n" if out else "")


def _build_scenario_decorator(
    *,
    scenario_def: ScenarioDef,
    extraction: ExtractionConfig,
    fn_name: str,
    regression_id: str,
) -> ast.Call:
    tag_list = list(extraction.add_tags) if extraction.add_tags else ["regression"]
    tag_elts: list[ast.expr] = [ast.Constant(value=t) for t in tag_list]
    keywords: list[ast.keyword] = [
        ast.keyword(arg="regression_id", value=ast.Constant(value=regression_id)),
        ast.keyword(arg="tags", value=ast.Tuple(elts=tag_elts, ctx=ast.Load())),
    ]
    if scenario_def.agent_fixture:
        keywords.append(
            ast.keyword(
                arg="agent_fixture", value=ast.Constant(value=scenario_def.agent_fixture)
            )
        )
    if scenario_def.user_fixture:
        keywords.append(
            ast.keyword(arg="user_fixture", value=ast.Constant(value=scenario_def.user_fixture))
        )
    if scenario_def.timeout_s is not None:
        keywords.append(
            ast.keyword(arg="timeout_s", value=ast.Constant(value=scenario_def.timeout_s))
        )
    return ast.Call(
        func=ast.Attribute(value=ast.Name(id="ek", ctx=ast.Load()), attr="scenario", ctx=ast.Load()),
        args=[],
        keywords=keywords,
    )


def extract_regression(
    *,
    scenario_def: ScenarioDef,
    failure_signature: dict[str, Any],
    extraction: ExtractionConfig,
    regression_id: str,
    shrunk_user_turns: tuple[str, ...] | None = None,
    body_steps: tuple[_Step, ...] | None = None,
    concrete_per_generative_step: dict[int, tuple[str, ...]] | None = None,
) -> ExtractionResult:
    _ = failure_signature
    if body_steps is not None and concrete_per_generative_step is not None:
        return _extract_concretise_ast(
            scenario_def=scenario_def,
            extraction=extraction,
            regression_id=regression_id,
            body_steps=body_steps,
            concrete_per_generative_step=concrete_per_generative_step,
        )
    if not shrunk_user_turns:
        return ExtractionResult(
            status="noop",
            regression_id=regression_id,
            message="no user turns to extract",
            fingerprint=None,
            function_name=None,
        )
    return _extract_legacy_user_messages_only(
        scenario_def=scenario_def,
        extraction=extraction,
        regression_id=regression_id,
        shrunk_user_turns=shrunk_user_turns,
    )


def _extract_legacy_user_messages_only(
    *,
    scenario_def: ScenarioDef,
    extraction: ExtractionConfig,
    regression_id: str,
    shrunk_user_turns: tuple[str, ...],
) -> ExtractionResult:
    target = _target_path(scenario_def, extraction)
    fingerprint = _fingerprint_for_turns(regression_id, shrunk_user_turns)
    fn_name = "regression_" + re.sub(r"[^0-9a-zA-Z_]+", "_", regression_id).strip("_")
    if not fn_name.isidentifier():
        fn_name = "regression_extracted"

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        original = target.read_text(encoding="utf-8") if target.exists() else ""
    except OSError as e:
        return ExtractionResult(
            status="errored",
            regression_id=regression_id,
            message=f"cannot read target: {e}",
            fingerprint=None,
            function_name=None,
        )

    if extraction.duplicate_policy == "skip" and (
        regression_id in original or _has_fingerprint(original, fingerprint)
    ):
        return ExtractionResult(
            status="skipped_duplicate",
            regression_id=regression_id,
            message="matching regression already present",
            fingerprint=fingerprint,
            function_name=fn_name,
        )

    tag_tuple = tuple(extraction.add_tags) if extraction.add_tags else ("regression",)
    tags_repr = "(" + ", ".join(repr(t) for t in tag_tuple) + ")"

    uniq_params: list[str] = []
    for p in scenario_def.fixture_param_names:
        if p not in uniq_params:
            uniq_params.append(p)
    if "s" not in uniq_params:
        uniq_params.insert(0, "s")
    params_joined = ", ".join(uniq_params)

    body_lines: list[str] = []
    for line in shrunk_user_turns:
        esc = json.dumps(line, ensure_ascii=False)
        body_lines.append(f"    s.user_message({esc})")

    body = "\n".join(body_lines) if body_lines else "    pass"

    af = (
        f"agent_fixture={json.dumps(scenario_def.agent_fixture)}, "
        if scenario_def.agent_fixture
        else ""
    )
    uf = (
        f"user_fixture={json.dumps(scenario_def.user_fixture)}, "
        if scenario_def.user_fixture
        else ""
    )

    block = f'''


# --- agent-spec-kit regression extraction: {regression_id} (fingerprint={fingerprint}) ---
@ek.scenario(
    {af}{uf}
    regression_id={json.dumps(regression_id)},
    tags={tags_repr},
)
async def {fn_name}({params_joined}):
{body}
'''
    new_src = _merge_import_block(original, "import agent_spec_kit as ek")
    new_src = new_src.rstrip() + block
    if target.exists():
        try:
            ast.parse(new_src)
        except SyntaxError as e:
            return ExtractionResult(
                status="errored",
                regression_id=regression_id,
                message=f"syntax error after splice: {e}",
                fingerprint=fingerprint,
                function_name=fn_name,
            )

    try:
        target.write_text(new_src, encoding="utf-8")
    except OSError as e:
        return ExtractionResult(
            status="errored",
            regression_id=regression_id,
            message=str(e),
            fingerprint=fingerprint,
            function_name=fn_name,
        )

    return ExtractionResult(
        status="written",
        regression_id=regression_id,
        message=str(target),
        fingerprint=fingerprint,
        function_name=fn_name,
    )


def _extract_concretise_ast(
    *,
    scenario_def: ScenarioDef,
    extraction: ExtractionConfig,
    regression_id: str,
    body_steps: tuple[_Step, ...],
    concrete_per_generative_step: dict[int, tuple[str, ...]],
) -> ExtractionResult:
    target = _target_path(scenario_def, extraction)
    fingerprint = _fingerprint_concrete(regression_id, concrete_per_generative_step)
    fn_name = "regression_" + re.sub(r"[^0-9a-zA-Z_]+", "_", regression_id).strip("_")
    if not fn_name.isidentifier():
        fn_name = "regression_extracted"

    src_path = Path(scenario_def.source)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        original_target = target.read_text(encoding="utf-8") if target.exists() else ""
        source_text = src_path.read_text(encoding="utf-8")
    except OSError as e:
        return ExtractionResult(
            status="errored",
            regression_id=regression_id,
            message=f"cannot read source or target: {e}",
            fingerprint=None,
            function_name=None,
        )

    if extraction.duplicate_policy == "skip" and (
        regression_id in original_target or _has_fingerprint(original_target, fingerprint)
    ):
        return ExtractionResult(
            status="skipped_duplicate",
            regression_id=regression_id,
            message="matching regression already present",
            fingerprint=fingerprint,
            function_name=fn_name,
        )

    try:
        tree = ast.parse(source_text)
    except SyntaxError as e:
        return ExtractionResult(
            status="errored",
            regression_id=regression_id,
            message=f"cannot parse scenario source: {e}",
            fingerprint=None,
            function_name=None,
        )

    fn_name_src = scenario_def.fn.__name__
    fn_node: ast.AsyncFunctionDef | None = None
    for node in tree.body:
        if isinstance(node, ast.AsyncFunctionDef) and node.name == fn_name_src:
            fn_node = node
            break
    if fn_node is None:
        return ExtractionResult(
            status="errored",
            regression_id=regression_id,
            message=f"async function {fn_name_src!r} not found in {src_path}",
            fingerprint=None,
            function_name=None,
        )

    preamble_stmts = _collect_scenario_preamble(fn_node)
    chain_calls = _collect_scenario_chain_calls(fn_node)
    if not chain_calls:
        return ExtractionResult(
            status="errored",
            regression_id=regression_id,
            message="scenario body: could not collect any scenario chain calls",
            fingerprint=None,
            function_name=None,
        )

    if len(chain_calls) != len(body_steps):
        return ExtractionResult(
            status="errored",
            regression_id=regression_id,
            message=(
                f"AST chain length {len(chain_calls)} does not match recorded steps {len(body_steps)}"
            ),
            fingerprint=None,
            function_name=None,
        )

    partial = False
    expr: ast.expr = ast.Name(id="s", ctx=ast.Load())
    skip_names = frozenset({"s", "True", "False", "None"})
    extra_imports: set[str] = set()
    needs_match_alias = False

    for i, (call_tmpl, st) in enumerate(zip(chain_calls, body_steps, strict=True)):
        if isinstance(st, (_FuzzConversationStep, _SimulateStep)):
            turns = concrete_per_generative_step.get(i, ())
            for msg in turns:
                expr = ast.Call(
                    func=ast.Attribute(value=expr, attr="user_message", ctx=ast.Load()),
                    args=[ast.Constant(value=msg)],
                    keywords=[],
                )
        else:
            if _has_lambda(call_tmpl):
                partial = True
            try:
                expr = _rebase_call_chain(expr, call_tmpl)
            except TypeError:
                return ExtractionResult(
                    status="errored",
                    regression_id=regression_id,
                    message=f"unsupported call shape at step {i}",
                    fingerprint=None,
                    function_name=None,
                )
            names = _collect_load_names(call_tmpl, skip=skip_names)
            for n in names:
                if n == "m":
                    needs_match_alias = True
                    continue
                if n == "ek":
                    continue
                extra_imports.add(n)

    for st in preamble_stmts:
        for n in _collect_load_names(st, skip=skip_names):
            if n == "m":
                needs_match_alias = True
                continue
            if n == "ek":
                continue
            extra_imports.add(n)

    mod = importlib.import_module(scenario_def.module)
    import_lines: list[str] = []
    for sym in sorted(extra_imports):
        if sym in getattr(mod, "__dict__", {}) and not sym.startswith("_"):
            import_lines.append(f"from {scenario_def.module} import {sym}")

    dec = _build_scenario_decorator(
        scenario_def=scenario_def,
        extraction=extraction,
        fn_name=fn_name,
        regression_id=regression_id,
    )
    params = [ast.arg("s")]
    for pname in scenario_def.fixture_param_names:
        if pname == "s":
            continue
        params.append(ast.arg(pname))
    new_fn = ast.AsyncFunctionDef(
        name=fn_name,
        args=ast.arguments(
            posonlyargs=[],
            args=params,
            kwonlyargs=[],
            kw_defaults=[],
            defaults=[],
            kwarg=None,
            vararg=None,
        ),
        body=[*preamble_stmts, ast.Expr(value=expr)],
        decorator_list=[dec],
        returns=None,
        type_params=[],
    )
    ast.fix_missing_locations(new_fn)

    try:
        block_src = ast.unparse(new_fn)
    except Exception as e:  # noqa: BLE001
        return ExtractionResult(
            status="errored",
            regression_id=regression_id,
            message=f"unparse failed: {e}",
            fingerprint=None,
            function_name=None,
        )
    block_src = _prettify_unparsed_block_src(block_src)

    header = _leading_import_lines(source_text)
    if "import agent_spec_kit as ek" not in header and "import agent_spec_kit as ek" not in original_target:
        header = _merge_import_block(header, "import agent_spec_kit as ek").strip() + "\n\n"
    else:
        header = header.rstrip() + "\n\n" if header.strip() else ""
    if needs_match_alias:
        if (
            "import agent_spec_kit.match as m" not in header
            and "import agent_spec_kit.match as m" not in original_target
        ):
            header = _merge_import_block(header, "import agent_spec_kit.match as m").strip() + "\n\n"

    extra_block = "\n".join(import_lines)
    if extra_block:
        header = header.rstrip() + "\n" + extra_block + "\n\n"

    comment = f"\n\n# --- agent-spec-kit regression extraction: {regression_id} (fingerprint={fingerprint}) ---\n"
    if partial:
        comment += "# TODO: action/assert uses a lambda or non-importable callable; review manually.\n"

    new_src = (original_target.rstrip() + "\n" if original_target else "") + header + comment + block_src + "\n"

    try:
        ast.parse(new_src)
    except SyntaxError as e:
        return ExtractionResult(
            status="errored",
            regression_id=regression_id,
            message=f"syntax error after splice: {e}",
            fingerprint=fingerprint,
            function_name=fn_name,
        )

    try:
        target.write_text(new_src, encoding="utf-8")
    except OSError as e:
        return ExtractionResult(
            status="errored",
            regression_id=regression_id,
            message=str(e),
            fingerprint=fingerprint,
            function_name=fn_name,
        )

    status: Literal["written", "partial"] = "partial" if partial else "written"
    return ExtractionResult(
        status=status,
        regression_id=regression_id,
        message=str(target),
        fingerprint=fingerprint,
        function_name=fn_name,
    )


__all__ = ["ExtractionResult", "extract_regression"]
