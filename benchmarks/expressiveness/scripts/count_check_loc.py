#!/usr/bin/env python3
"""Count lines between CHECK_START and CHECK_END markers per framework file."""

from __future__ import annotations

import re
from pathlib import Path

_EXPR = Path(__file__).resolve().parents[1]
IMPL = _EXPR / "implementations"

# Python: # CHECK_START / # CHECK_END
PY_START = re.compile(r"^\s*#\s*CHECK_START\s*$")
PY_END = re.compile(r"^\s*#\s*CHECK_END\s*$")

# Promptfoo YAML assertions: // CHECK_START / // CHECK_END
JS_START = re.compile(r"^\s*//\s*CHECK_START\s*$")
JS_END = re.compile(r"^\s*//\s*CHECK_END\s*$")

# def test_c05_..., def eval_c02_..., score_c06 wrapper, etc.
DEF_CHECK = re.compile(
    r"^\s*(?:async\s+)?def\s+(?:test_|eval_|score_)?c(\d{2})\w*",
    re.IGNORECASE,
)

# promptfooconfig: check_id: C05  or  vars: {check_id: C05}
YAML_CHECK_ID = re.compile(r"check_id:\s*(C\d{2})", re.IGNORECASE)

# assert_c11.py
ASSERT_FILE_CHECK = re.compile(r"assert_c(\d{2})\.py$", re.IGNORECASE)


def _normalize_cid(raw: str) -> str:
    n = raw.upper().lstrip("C")
    return f"C{int(n):02d}"


def count_in_python(path: Path) -> dict[str, int]:
    lines = path.read_text(encoding="utf-8").splitlines()
    counts: dict[str, int] = {}
    current_check: str | None = None
    m_assert = ASSERT_FILE_CHECK.search(path.name)
    if m_assert:
        current_check = _normalize_cid(m_assert.group(1))
    in_block = False
    block_lines = 0

    def flush() -> None:
        nonlocal block_lines, current_check
        if block_lines > 0:
            key = current_check if current_check is not None else "__anon__"
            counts[key] = counts.get(key, 0) + block_lines
        block_lines = 0

    for line in lines:
        m_def = DEF_CHECK.match(line)
        if m_def:
            flush()
            current_check = _normalize_cid(m_def.group(1))
        if PY_START.match(line):
            in_block = True
            block_lines = 0
            continue
        if PY_END.match(line):
            flush()
            in_block = False
            continue
        if in_block and line.strip() and not line.strip().startswith("#"):
            block_lines += 1
    flush()
    return counts


def count_in_promptfoo_yaml(path: Path) -> dict[str, int]:
    lines = path.read_text(encoding="utf-8").splitlines()
    counts: dict[str, int] = {}
    current_check: str | None = None
    in_block = False
    block_lines = 0

    def flush() -> None:
        nonlocal block_lines, current_check
        if block_lines > 0:
            key = current_check if current_check is not None else "__anon__"
            counts[key] = counts.get(key, 0) + block_lines
        block_lines = 0

    for line in lines:
        m_id = YAML_CHECK_ID.match(line)
        if m_id:
            current_check = _normalize_cid(m_id.group(1))
        if JS_START.match(line):
            in_block = True
            block_lines = 0
            continue
        if JS_END.match(line):
            flush()
            in_block = False
            continue
        if in_block and line.strip() and not line.strip().startswith("//"):
            block_lines += 1
    flush()
    return counts


def framework_from_path(path: Path) -> str:
    parts = path.parts
    idx = parts.index("implementations")
    return parts[idx + 1]


def main() -> None:
    totals: dict[str, dict[str, int]] = {}

    for py in sorted(IMPL.rglob("*.py")):
        if py.name == "__init__.py":
            continue
        rel = py.relative_to(IMPL)
        if rel.parts[0] not in (
            "agent_spec_kit",
            "pytest_plain",
            "langsmith",
            "pydantic_evals",
            "braintrust",
        ):
            continue
        if "test_" not in py.name and py.name not in ("evaluators.py", "scorers.py"):
            continue
        fw = framework_from_path(py)
        counts = count_in_python(py)
        if not counts:
            continue
        totals.setdefault(fw, {})
        for k, v in counts.items():
            totals[fw][k] = totals[fw].get(k, 0) + v

    pf_dir = IMPL / "promptfoo"
    pf_counts: dict[str, int] = {}
    pf_yaml = pf_dir / "promptfooconfig.yaml"
    yaml_check_ids: list[str] = []
    if pf_yaml.is_file():
        for line in pf_yaml.read_text(encoding="utf-8").splitlines():
            m_id = YAML_CHECK_ID.search(line)
            if m_id:
                yaml_check_ids.append(_normalize_cid(m_id.group(1)))
        for k, v in count_in_promptfoo_yaml(pf_yaml).items():
            pf_counts[k] = pf_counts.get(k, 0) + v
    for py in sorted(pf_dir.glob("assert_*.py")):
        for k, v in count_in_python(py).items():
            if k == "__anon__" and yaml_check_ids:
                for cid in yaml_check_ids:
                    pf_counts[cid] = pf_counts.get(cid, 0) + v
            else:
                pf_counts[k] = pf_counts.get(k, 0) + v
    if pf_counts:
        totals["promptfoo"] = pf_counts

    for fw, counts in sorted(totals.items()):
        print(f"[{fw}]")
        for cid in sorted(counts):
            print(f"  {cid}: {counts[cid]}")


if __name__ == "__main__":
    main()
