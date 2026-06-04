"""Extract CHECK_START/CHECK_END blocks and LOC counts per framework port."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_EXPR = Path(__file__).resolve().parents[1]
IMPL = _EXPR / "implementations"

FRAMEWORKS = [
    "agent_spec_kit",
    "pytest_plain",
    "langsmith",
    "pydantic_evals",
    "promptfoo",
    "braintrust",
]

_PY_FRAMEWORKS = [fw for fw in FRAMEWORKS if fw != "promptfoo"]

PY_START = re.compile(r"^\s*#\s*CHECK_START\s*$")
PY_END = re.compile(r"^\s*#\s*CHECK_END\s*$")
JS_START = re.compile(r"^\s*(?://|#\s*//)\s*CHECK_START\s*$")
JS_END = re.compile(r"^\s*(?://|#\s*//)\s*CHECK_END\s*$")
DEF_CHECK = re.compile(
    r"^\s*(?:async\s+)?def\s+(?:test_|eval_|score_)?c(\d{2})\w*",
    re.IGNORECASE,
)
YAML_CHECK_ID = re.compile(r"check_id:\s*(C\d{2})", re.IGNORECASE)
CHECK_TAG = re.compile(r"^\s*#\s*check:\s*C(\d{2})\s*$", re.IGNORECASE)
ASSERT_FILE_CHECK = re.compile(r"assert_c(\d{2})\.py$", re.IGNORECASE)

# Python port files (native single-file layouts + per-framework tests).
_PORT_PY_NAMES = frozenset(
    {
        "dataset.py",
        "experiment.py",
        "evaluators.py",
        "scorers.py",
        "test_checks.py",
        "test_canonical_checks.py",
    }
)
_SKIP_PY_NAMES = frozenset(
    {
        "provider.py",
        "trace_spans.py",
        "trajectory_bridge.py",
        "span_tree_bridge.py",
        "test_golden_asserts.py",
        "assert_c11.py",
        "assert_c12.py",
    }
)


def normalize_cid(raw: str) -> str:
    n = raw.upper().lstrip("C")
    return f"C{int(n):02d}"


@dataclass(frozen=True, slots=True)
class CheckSnippet:
    check_id: str
    framework: str
    source_path: str
    snippet_text: str
    loc: int


def _countable_line(line: str, comment_prefix: str) -> bool:
    s = line.strip()
    return bool(s) and not s.startswith(comment_prefix)


def _parse_python_blocks(path: Path) -> dict[str, tuple[str, int]]:
    """Return check_id -> (snippet_text, loc) for one Python file."""
    lines = path.read_text(encoding="utf-8").splitlines()
    out: dict[str, tuple[str, int]] = {}
    current_check: str | None = None
    m_assert = ASSERT_FILE_CHECK.search(path.name)
    if m_assert:
        current_check = normalize_cid(m_assert.group(1))
    in_block = False
    block_lines: list[str] = []

    def flush() -> None:
        nonlocal block_lines, current_check
        if not block_lines:
            return
        key = current_check if current_check is not None else "__anon__"
        text = "\n".join(block_lines)
        loc = sum(1 for ln in block_lines if _countable_line(ln, "#"))
        if key in out:
            prev_text, prev_loc = out[key]
            out[key] = (prev_text + "\n" + text, prev_loc + loc)
        else:
            out[key] = (text, loc)
        block_lines = []

    for line in lines:
        m_tag = CHECK_TAG.match(line)
        if m_tag:
            current_check = normalize_cid(m_tag.group(1))
        m_def = DEF_CHECK.match(line)
        if m_def:
            flush()
            current_check = normalize_cid(m_def.group(1))
        if PY_START.match(line):
            in_block = True
            block_lines = []
            continue
        if PY_END.match(line):
            flush()
            in_block = False
            continue
        if in_block:
            block_lines.append(line)
    flush()
    return out


def _parse_promptfoo_yaml(path: Path) -> dict[str, tuple[str, int]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    out: dict[str, tuple[str, int]] = {}
    current_check: str | None = None
    in_block = False
    block_lines: list[str] = []

    def flush() -> None:
        nonlocal block_lines, current_check
        if not block_lines:
            return
        key = current_check if current_check is not None else "__anon__"
        text = "\n".join(block_lines)
        loc = sum(1 for ln in block_lines if _countable_line(ln, "//"))
        if key in out:
            prev_text, prev_loc = out[key]
            out[key] = (prev_text + "\n" + text, prev_loc + loc)
        else:
            out[key] = (text, loc)
        block_lines = []

    for line in lines:
        m_id = YAML_CHECK_ID.search(line)
        if m_id:
            current_check = normalize_cid(m_id.group(1))
        if JS_START.match(line):
            in_block = True
            block_lines = []
            continue
        if JS_END.match(line):
            flush()
            in_block = False
            continue
        if in_block:
            block_lines.append(line)
    flush()
    return out


def framework_from_path(path: Path) -> str:
    parts = path.parts
    idx = parts.index("implementations")
    return parts[idx + 1]


def loc_by_framework() -> dict[str, dict[str, int]]:
    """LOC counts per framework and check_id (same totals as legacy count_check_loc)."""
    snippets = extract_all_snippets()
    result: dict[str, dict[str, int]] = {}
    for s in snippets:
        result.setdefault(s.framework, {})[s.check_id] = s.loc
    return result


def extract_all_snippets() -> list[CheckSnippet]:
    """One snippet per (check_id, framework) — 72 cells for C01–C12 × six frameworks."""
    snippets: list[CheckSnippet] = []

    for py in sorted(IMPL.rglob("*.py")):
        if py.name == "__init__.py" or py.name in _SKIP_PY_NAMES:
            continue
        rel = py.relative_to(IMPL)
        if rel.parts[0] not in _PY_FRAMEWORKS:
            continue
        if py.name not in _PORT_PY_NAMES:
            continue
        fw = framework_from_path(py)
        for cid, (text, loc) in _parse_python_blocks(py).items():
            if cid == "__anon__":
                continue
            snippets.append(
                CheckSnippet(
                    check_id=cid,
                    framework=fw,
                    source_path=str(py.relative_to(_EXPR)),
                    snippet_text=text,
                    loc=loc,
                )
            )

    pf_dir = IMPL / "promptfoo"
    pf_yaml = pf_dir / "promptfooconfig.yaml"
    yaml_check_ids: list[str] = []
    merged: dict[str, tuple[str, int]] = {}
    if pf_yaml.is_file():
        for line in pf_yaml.read_text(encoding="utf-8").splitlines():
            m_id = YAML_CHECK_ID.search(line)
            if m_id:
                yaml_check_ids.append(normalize_cid(m_id.group(1)))
        for cid, pair in _parse_promptfoo_yaml(pf_yaml).items():
            if cid == "__anon__":
                continue
            merged[cid] = pair
    for py in sorted(pf_dir.glob("assert_*.py")):
        for cid, (text, loc) in _parse_python_blocks(py).items():
            if cid == "__anon__" and yaml_check_ids:
                for yid in yaml_check_ids:
                    if yid in merged:
                        pt, pl = merged[yid]
                        merged[yid] = (pt + "\n" + text, pl + loc)
                    else:
                        merged[yid] = (text, loc)
            elif cid != "__anon__":
                if cid in merged:
                    pt, pl = merged[cid]
                    merged[cid] = (pt + "\n" + text, pl + loc)
                else:
                    merged[cid] = (text, loc)

    for cid in sorted(merged):
        text, loc = merged[cid]
        snippets.append(
            CheckSnippet(
                check_id=cid,
                framework="promptfoo",
                source_path="implementations/promptfoo",
                snippet_text=text,
                loc=loc,
            )
        )

    return sorted(snippets, key=lambda s: (s.check_id, s.framework))
