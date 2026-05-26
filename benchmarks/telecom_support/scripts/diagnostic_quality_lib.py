"""Parse fault-detection failure panels, deterministic metrics, and LLM specificity scoring."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Awaitable

from pydantic import BaseModel, Field

from scripts.fault_detection_lib import (
    BENCH,
    FAULT_DIR,
    ORACLE_FROM_KIND,
    enrich_detection,
    load_fault_matrix,
    parse_fault_detection_log,
)

DIAG_DIR = BENCH / "diagnostic_comparison"
FAILURES_DIR = FAULT_DIR / "diagnostic_failures"
RECORDS_PATH = FAULT_DIR / "diagnostic_records.json"
META_PATH = FAULT_DIR / "diagnostic_extract_meta.json"
MESSAGES_PATH = DIAG_DIR / "failure_messages.yaml"

FRAMEWORKS = [
    "agent_spec_kit",
    "pytest_plain",
    "langsmith",
    "pydantic_evals",
    "promptfoo",
    "braintrust",
]

KNOWN_CHECKS = frozenset(
    {"assert_tool_calls", "assert_that", "assert_output", "forbid_tool_calls"}
)

_PANEL_FIELD_NAMES = frozenset(
    {"Check", "Where", "Path", "Expected", "Actual", "Agent errors"}
)

DIAGNOSTIC_SPECIFICITY_RUBRIC = """\
| Score | Meaning |
|------:|---------|
| 0 | Only says the run/eval failed with no check or lane hint. Examples: `assertion returned False`, bare PASS/FAIL, or a numeric score with no named check. |
| 1 | Identifies a broad category/lane only (output vs state vs trace/tooling) without naming which rule or eval failed. |
| 2 | Identifies *which* check/eval failed by name, but without enough detail to pinpoint the exact issue/cause. Examples: `assert_tool_calls`, `assert_output`, “expected zero credits”, `{'key': 'f10_output_rubric', 'score': 0}`, `{'key': 'f07_forbidden_tools', 'score': 0}`. |
| 3 | Adds meaningful localisation/precision: where it failed (turn/node/tool index/state row) and/or explicit expected vs actual evidence, but may still miss full cause (especially for structured objects). |
| 4 | Top score. Easy to diagnose to the exact issue and cause from the message alone. |
|   | - *Structured-object mismatches* (tool args, forbidden tools, JSON/state diffs): exact field/path plus expected vs actual (missing/extra key, wrong value/order). |
|   | - *Text/criterion mismatches* (`assert_output`, LLM rubrics): failed criterion, expected vs actual (or pass/fail counts), and why the requirement was not satisfied; exact field/path not required. |

Framework-port calibration (minimal messages are not all score 0):
- **Score 0**: `assertion returned False` — no check name, no lane, no expected/actual.
- **Score 1**: `{'key': 'tool_sequence', 'score': 0}` or `{'key': 'state_oracle', 'score': 0}` — the key implies trace vs state lane only.
- **Score 2**: `{'key': 'f10_output_rubric', 'score': 0}` or `{'key': 'f02_tool_sequence', 'score': 0}` — the key names the specific eval that failed (output rubric, tool sequence, forbidden tools, etc.), even though location and expected/actual are absent. This is better than score 0/1 but not a strong diagnostic.

Maximum score is 4. Do not award higher scores for extraction hooks, replay IDs, or signature stability.
"""

_PANEL_TITLE_RE = re.compile(
    r"FAIL\s+test_f(\d+)_t(\d+)_(full|trace|state|output)\s+\[(\d+)/(\d+)\]",
    re.IGNORECASE,
)
_HEADLINE_RE = re.compile(
    r"^(PASS|FAIL)\s+test_f(\d+)_t(\d+)_(full|trace|state|output)\s+\[(\d+)/(\d+)\]",
    re.IGNORECASE,
)
_BOX_START = re.compile(r"^╭[─-]+ FAIL ")
_BOX_END = re.compile(r"^╰[─-]+")
_FIELD_RE = re.compile(r"^([^:]+):\s*(.*)$")
_TOOL_LINE_RE = re.compile(r"├──\s+(\w+)")


@dataclass
class FailureWitness:
    scenario: str
    family: str
    task: str
    oracle: str
    check: str = ""
    where: str = ""
    path: str = ""
    expected: str = ""
    actual: str = ""
    headline: str = ""
    panel_text: str = ""
    event_trace_text: str = ""
    state_message: str = ""
    output_text: str = ""

    def slot_key(self, framework: str) -> str:
        return f"{self.family}|{self.task}|{framework}|{self.oracle}"


class SpecificityScore(BaseModel):
    specificity_score: int = Field(ge=0, le=4)
    rationale: str = ""


DIAGNOSTIC_JUDGE_SYSTEM = (
    "You evaluate how well an automated test failure message helps a developer "
    "diagnose the exact issue and cause. Use the rubric levels 0-4. "
    "Minimal framework ports that name the failing eval via a `key` field "
    "(e.g. f10_output_rubric, tool_sequence, forbidden_tools) are typically "
    "score 1-2, not 0. Bare 'assertion returned False' with no check name is score 0. "
    "Score 4 is the maximum."
)


def _strip_box_margin(line: str) -> str:
    s = line.rstrip()
    if s.endswith("│"):
        s = s[:-1].rstrip()
    if s.startswith("│"):
        s = s[1:].lstrip()
    return s


def _scenario_meta(scenario: str) -> tuple[str, str, str]:
    m = re.match(r"test_f(\d+)_t(\d+)_(full|trace|state|output)$", scenario, re.I)
    if not m:
        raise ValueError(f"invalid scenario name: {scenario}")
    family = f"F{int(m.group(1)):02d}"
    task = f"T{int(m.group(2)):02d}"
    oracle = ORACLE_FROM_KIND[m.group(3).lower()]
    return family, task, oracle


def parse_failure_panels(log_text: str) -> dict[str, FailureWitness]:
    """Parse Rich FAIL boxes and headline summaries from a fault-detection log."""
    headlines: dict[str, str] = {}
    for line in log_text.splitlines():
        m = _HEADLINE_RE.match(line.strip())
        if not m:
            continue
        fnum, tnum, kind = m.group(2), m.group(3), m.group(4)
        scenario = f"test_f{fnum}_t{tnum}_{kind.lower()}"
        headlines[scenario] = line.strip()

    witnesses: dict[str, FailureWitness] = {}
    lines = log_text.splitlines()
    i = 0
    while i < len(lines):
        if not _BOX_START.match(lines[i]):
            i += 1
            continue
        title_line = lines[i]
        tm = _PANEL_TITLE_RE.search(title_line)
        if not tm:
            i += 1
            continue
        fnum, tnum, kind = tm.group(1), tm.group(2), tm.group(3)
        scenario = f"test_f{fnum}_t{tnum}_{kind.lower()}"
        family, task, oracle = _scenario_meta(scenario)
        box_lines = [title_line]
        i += 1
        while i < len(lines) and not _BOX_END.match(lines[i]):
            box_lines.append(lines[i])
            i += 1
        if i < len(lines):
            box_lines.append(lines[i])
            i += 1
        panel_text = "\n".join(box_lines)
        witness = FailureWitness(
            scenario=scenario,
            family=family,
            task=task,
            oracle=oracle,
            headline=headlines.get(scenario, ""),
            panel_text=panel_text,
        )
        _fill_witness_fields(witness, box_lines)
        witnesses[scenario] = witness
    return witnesses


def _fill_witness_fields(witness: FailureWitness, box_lines: list[str]) -> None:
    current_key: str | None = None
    value_lines: list[str] = []
    trace_started = False
    trace_lines: list[str] = []

    def flush_field() -> None:
        nonlocal current_key, value_lines
        if not current_key:
            value_lines = []
            return
        text = "\n".join(value_lines).strip()
        text = re.sub(r"\s*│\s*$", "", text, flags=re.MULTILINE).strip()
        key = current_key.lower().replace(" ", "_")
        if key == "check":
            witness.check = text
        elif key == "where":
            witness.where = text
        elif key == "path":
            witness.path = text
        elif key == "expected":
            witness.expected = text
        elif key == "actual":
            witness.actual = text
        elif key == "agent_errors":
            witness.output_text = text
        current_key = None
        value_lines = []

    for raw in box_lines[1:]:
        line = _strip_box_margin(raw)
        if not line:
            continue
        dash_only = set(line.replace(" ", "")) <= {"─"}
        if dash_only and not value_lines:
            flush_field()
            continue
        if dash_only:
            continue
        if line.startswith("Event trace"):
            flush_field()
            trace_started = True
            trace_lines = []
            continue
        if trace_started:
            if line.startswith("Check:") or line.startswith("Where:"):
                trace_started = False
            else:
                trace_lines.append(line)
                continue
        fm = _FIELD_RE.match(line)
        if fm and fm.group(1).strip() in _PANEL_FIELD_NAMES:
            flush_field()
            current_key = fm.group(1).strip()
            rest = fm.group(2).strip()
            value_lines = [rest] if rest else []
        elif current_key:
            value_lines.append(line)
    flush_field()
    witness.event_trace_text = "\n".join(trace_lines).strip()
    if witness.check == "assert_that" and witness.expected.startswith("assert_that failed:"):
        witness.state_message = witness.expected
    elif "assert_that failed:" in witness.expected:
        witness.state_message = witness.expected


def deterministic_metrics(witness: FailureWitness) -> dict[str, Any]:
    """Compute non-LLM table columns from a parsed witness."""
    check = witness.check.strip()
    failed_req = check in KNOWN_CHECKS or (
        bool(check) and witness.headline and check in witness.headline
    )
    trace_or_state = bool(
        witness.path.strip()
        or (witness.where and ("turn" in witness.where.lower() or "assert" in witness.where.lower()))
        or _TOOL_LINE_RE.search(witness.event_trace_text or "")
        or witness.state_message.strip()
    )
    field_path = bool(re.search(r"\$\[", witness.path))
    exp = witness.expected.strip()
    act = witness.actual.strip()
    eva = bool(
        (exp and act and exp != act)
        or re.search(r"expected .+ found", witness.state_message, re.I)
        or re.search(r"found \d+", witness.state_message, re.I)
    )
    nodes = 0
    if witness.event_trace_text:
        for line in witness.event_trace_text.splitlines():
            if _TOOL_LINE_RE.search(line):
                nodes += 1
                if nodes >= 1:
                    break
        if nodes == 0:
            nodes = min(20, len(witness.event_trace_text.splitlines()))
    lines_detail = _lines_to_useful_detail(witness)
    sig_src = f"{witness.scenario}|{check}|{witness.path}|{witness.headline[:120]}"
    stable_sig = bool(check) and bool(hashlib.sha256(sig_src.encode()).hexdigest())
    return {
        "failed_requirement_named": failed_req,
        "trace_node_identified": trace_or_state,
        "field_path_shown": field_path,
        "expected_vs_actual_shown": eva,
        "nodes_to_inspect": nodes,
        "lines_to_useful_detail": lines_detail,
        "stable_signature": stable_sig,
    }


def _lines_to_useful_detail(witness: FailureWitness) -> int:
    if not witness.panel_text:
        return 0
    lines = witness.panel_text.splitlines()
    for idx, line in enumerate(lines):
        if "Expected:" in line or "assert_that failed:" in line:
            return max(1, idx + 1)
    return len(lines)


def diagnostic_targets(matrix: dict[str, Any] | None = None) -> dict[str, str]:
    matrix = matrix or load_fault_matrix()
    out: dict[str, str] = {}
    for family, spec in matrix.get("families", {}).items():
        target = spec.get("diagnostic_target")
        if target:
            out[family] = str(target)
    return out


def load_results_enriched(
    results_path: Path,
    eligibility_path: Path,
) -> dict[str, dict[str, Any]]:
    results = json.loads(results_path.read_text(encoding="utf-8"))
    eligibility = json.loads(eligibility_path.read_text(encoding="utf-8"))
    return enrich_detection(results, eligibility)


def iter_scored_slots(
    results: dict[str, dict[str, Any]],
    *,
    main_table_only: bool = False,
    framework: str | None = None,
) -> list[tuple[str, str, str, str, dict[str, Any]]]:
    """Yield (family, task, framework, oracle, result_rec) for slots to process."""
    out: list[tuple[str, str, str, str, dict[str, Any]]] = []
    frameworks = [framework] if framework else FRAMEWORKS
    for key, rec in sorted(results.items()):
        if main_table_only:
            if not rec.get("detected") or rec.get("oracle") != "F":
                continue
        fam = rec["fault"]
        task = rec["task"]
        oracle = rec["oracle"]
        for fw in frameworks:
            out.append((fam, task, fw, oracle, rec))
    return out


def require_openai_key() -> None:
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        raise SystemExit(
            "OPENAI_API_KEY is required for diagnostic LLM scoring. "
            "Set the key or use --skip-llm with existing diagnostic_records.json."
        )


def _build_judge_user_prompt(
    *,
    failure_box_text: str,
    diagnostic_target: str,
    family: str,
    task: str,
    framework: str,
    oracle: str,
) -> str:
    return (
        f"{DIAGNOSTIC_SPECIFICITY_RUBRIC}\n\n"
        f"Fault family: {family}\n"
        f"Task: {task}\n"
        f"Framework: {framework}\n"
        f"Oracle: {oracle}\n"
        f"Ideal diagnostic target for this fault family:\n{diagnostic_target}\n\n"
        "Failure message (full box):\n"
        f"{failure_box_text[:10000]}\n\n"
        "Return specificity_score 0-4 and a short rationale citing evidence from the failure message."
    )


JudgeFn = Callable[..., Awaitable[SpecificityScore]]


async def assess_specificity_llm(
    *,
    failure_box_text: str,
    diagnostic_target: str,
    family: str,
    task: str,
    framework: str,
    oracle: str,
    model: str = "openai:gpt-5-nano",
    judge_fn: JudgeFn | None = None,
) -> SpecificityScore:
    if not failure_box_text.strip():
        raise ValueError("empty failure_box_text")
    if judge_fn is not None:
        return await judge_fn(
            failure_box_text=failure_box_text,
            diagnostic_target=diagnostic_target,
            family=family,
            task=task,
            framework=framework,
            oracle=oracle,
            model=model,
        )
    from agent_spec_kit.judges.structured import call_structured

    user = _build_judge_user_prompt(
        failure_box_text=failure_box_text,
        diagnostic_target=diagnostic_target,
        family=family,
        task=task,
        framework=framework,
        oracle=oracle,
    )
    return await call_structured(
        model=model,
        system=DIAGNOSTIC_JUDGE_SYSTEM,
        user=user,
        response_model=SpecificityScore,
    )


async def score_cells(
    cells: list[dict[str, Any]],
    *,
    model: str,
    concurrency: int = 8,
    skip_llm: bool = False,
    refresh_llm: bool = False,
    judge_fn: JudgeFn | None = None,
) -> list[dict[str, Any]]:
    sem = asyncio.Semaphore(concurrency)

    async def one(cell: dict[str, Any]) -> dict[str, Any]:
        if skip_llm and cell.get("llm_assessment"):
            return cell
        if not refresh_llm and cell.get("llm_assessment") and cell["llm_assessment"].get("specificity_score") is not None:
            return cell
        if not cell.get("failure_box_text", "").strip():
            cell["status"] = "no_failure_box"
            return cell
        async with sem:
            try:
                scored = await assess_specificity_llm(
                    failure_box_text=cell["failure_box_text"],
                    diagnostic_target=cell.get("diagnostic_target", ""),
                    family=cell["family"],
                    task=cell["task"],
                    framework=cell["framework"],
                    oracle=cell["oracle"],
                    model=model,
                    judge_fn=judge_fn,
                )
                cell["llm_assessment"] = {
                    "model": model,
                    "specificity_score": scored.specificity_score,
                    "rationale": scored.rationale,
                    "assessed_utc": datetime.now(UTC).isoformat(),
                }
                cell["status"] = "ok"
            except Exception as exc:
                cell["status"] = "llm_error"
                cell["llm_error"] = str(exc)
        return cell

    return await asyncio.gather(*[one(c) for c in cells])


def witness_to_dict(w: FailureWitness) -> dict[str, Any]:
    return asdict(w)
