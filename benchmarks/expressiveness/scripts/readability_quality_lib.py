"""LLM letter-grade scoring (A–D) for expressiveness check authoring clarity."""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Awaitable, Callable, Literal

from pydantic import BaseModel, field_validator

_EXPR = Path(__file__).resolve().parents[1]
RECORDS_PATH = _EXPR / "readability_records.json"
META_PATH = _EXPR / "readability_extract_meta.json"
CANONICAL_SPEC_PATH = _EXPR / "CANONICAL_SPEC.md"

RUBRIC_VERSION = "clarity-v6"

Grade = Literal["A", "B", "C", "D"]

AUTHORING_CLARITY_RUBRIC = """\
## Scope
Grade only the inlined check snippet (between CHECK_START and CHECK_END). Ignore symbols \
defined outside the snippet. Judge reading cost for a maintainer, not whether the policy \
could be reconstructed after careful study.

## What to weigh (one combined A–D grade)

**Immediate grasp** — Without mentally executing the code, is it obvious what is being \
required and how that requirement connects to the canonical policy?

**Scenario shape** — Does the excerpt show agent-facing stimulus and how the check attaches \
(user turns, `user_message`, staged dialogue, or an explicit scenario block)? Locating a \
tool inside a frozen trace and validating JSON is post-hoc inspection, not scenario shape. \
Such ports should not tie with specification DSLs that state the customer turn and expected \
tool/result together in one block.

**Surface form** — Are tools, fields, and constraints named declaratively in one place, or \
buried in lookup helpers, type guards, swallowed exceptions, and indirect returns?

## Calibration (apply strictly; do not anchor on framework labels)

Reserve **A** for excerpts that read like a compact specification a new maintainer could \
audit quickly: policy, stimulus or scenario hook, and constraints are visible together.

**A is not automatic** for short validators (jsonschema, BaseModel, span queries, boolean \
score returns) that omit agent stimulus—those are typically **B** (clear schema) or **C** \
(plumbing-heavy) when the specimen is scenario-shaped. Swallowed validation errors and \
`score: 0` returns without surfacing constraints in the excerpt lower surface-form clarity.

**B** means the policy is mostly visible after one modest indirection (single lookup layer, \
one schema block, one custom evaluator) but scenario shape is thin.

**C** means several mechanical steps or hidden context are required before the policy is clear, \
or the excerpt is mostly plumbing.

**D** means the excerpt does not convey what is tested or which properties matter.

Grade on reading cost relative to the canonical policy—not line count, not framework prestige, \
and not whether a patient reader could eventually infer the answer.

## Letter grades (A best, D worst)

| Grade | Authoring clarity |
|-------|-------------------|
| A | Specification-like: policy, scenario hook, and constraints visible together at a glance |
| B | Policy mostly clear after one modest procedural or contextual layer; weak scenario shape |
| C | Policy only after multiple mechanical steps; trace-only or plumbing-heavy |
| D | Does not convey what is tested, what the agent saw, or which properties matter |
"""

CLARITY_JUDGE_SYSTEM = (
    "You grade authoring clarity of inlined agent-evaluation check snippets. "
    "Apply the rubric strictly: reserve A for specification-like excerpts with visible "
    "scenario shape; penalize trace-only post-processing and swallowed failures even when "
    "constraints are technically present. Return one letter A–D and a brief rationale citing "
    "snippet evidence. Never return E or numeric scores."
)


class ClarityAssessment(BaseModel):
    clarity_grade: Grade
    rationale: str = ""

    @field_validator("clarity_grade", mode="before")
    @classmethod
    def _normalize_grade(cls, v: object) -> str:
        return normalize_grade(str(v))


# Back-compat alias for tests importing ReadabilityAssessment
ReadabilityAssessment = ClarityAssessment


def normalize_grade(raw: str) -> Grade:
    s = raw.strip().upper()
    if s in ("A", "B", "C", "D"):
        return s  # type: ignore[return-value]
    raise ValueError(f"invalid grade {raw!r}; expected A, B, C, or D")


def load_canonical_policies() -> dict[str, str]:
    text = CANONICAL_SPEC_PATH.read_text(encoding="utf-8")
    policies: dict[str, str] = {}
    for line in text.splitlines():
        m = re.match(r"^\|\s*(C\d{2})\s*\|\s*(.+?)\s*\|$", line)
        if m:
            policies[m.group(1).upper()] = m.group(2).strip()
    return policies


def cell_key(check_id: str, framework: str) -> str:
    return f"{check_id}|{framework}"


def snippet_hash(snippet_text: str) -> str:
    payload = f"{RUBRIC_VERSION}\n{snippet_text}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def require_openai_key() -> None:
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        raise SystemExit(
            "OPENAI_API_KEY is required for clarity LLM scoring. "
            "Set the key or use existing readability_records.json."
        )


def _build_judge_user_prompt(
    *,
    check_id: str,
    check_name: str,
    check_description: str,
    telecom_task: str | None,
    framework: str,
    canonical_policy: str,
    snippet_text: str,
    loc: int,
) -> str:
    task_line = f"Telecom exemplar task: {telecom_task}\n" if telecom_task else ""
    return (
        f"{AUTHORING_CLARITY_RUBRIC}\n\n"
        "---\n"
        f"Check id: {check_id}\n"
        f"Check name: {check_name}\n"
        f"Specimen description: {check_description}\n"
        f"{task_line}"
        "If this specimen concerns output text, tool trajectories, or structured tool results, "
        "downgrade ports whose snippet only inspects a trace blob unless agent stimulus appears "
        "inside the graded excerpt.\n"
        f"Framework port label: {framework}\n"
        f"Snippet size (non-comment LOC): {loc}\n\n"
        f"Canonical policy for this specimen:\n{canonical_policy}\n\n"
        "Inlined check snippet:\n"
        f"```\n{snippet_text[:12000]}\n```\n\n"
        "Return clarity_grade (A, B, C, or D) and a short rationale citing evidence from the snippet. "
        "Apply strict calibration: do not award A to trace-only ports when scenario shape is absent."
    )


JudgeFn = Callable[..., Awaitable[ClarityAssessment]]


async def assess_readability_llm(
    *,
    check_id: str,
    check_name: str,
    check_description: str,
    telecom_task: str | None,
    framework: str,
    canonical_policy: str,
    snippet_text: str,
    loc: int,
    model: str = "openai:gpt-5-mini",
    judge_fn: JudgeFn | None = None,
) -> ClarityAssessment:
    if not snippet_text.strip():
        raise ValueError("empty snippet_text")
    if judge_fn is not None:
        return await judge_fn(
            check_id=check_id,
            check_name=check_name,
            check_description=check_description,
            telecom_task=telecom_task,
            framework=framework,
            canonical_policy=canonical_policy,
            snippet_text=snippet_text,
            loc=loc,
            model=model,
        )
    from agent_spec_kit.judges.structured import call_structured

    user = _build_judge_user_prompt(
        check_id=check_id,
        check_name=check_name,
        check_description=check_description,
        telecom_task=telecom_task,
        framework=framework,
        canonical_policy=canonical_policy,
        snippet_text=snippet_text,
        loc=loc,
    )
    return await call_structured(
        model=model,
        system=CLARITY_JUDGE_SYSTEM,
        user=user,
        response_model=ClarityAssessment,
    )


def build_cells_from_snippets(
    snippets: list[Any],
    *,
    policies: dict[str, str],
    specimen_by_id: dict[str, Any],
) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    for snip in snippets:
        spec = specimen_by_id[snip.check_id]
        cells.append(
            {
                "key": cell_key(snip.check_id, snip.framework),
                "check_id": snip.check_id,
                "framework": snip.framework,
                "source_path": snip.source_path,
                "snippet_text": snip.snippet_text,
                "loc": snip.loc,
                "snippet_hash": snippet_hash(snip.snippet_text),
                "check_name": spec.name,
                "check_description": spec.description,
                "telecom_task": spec.telecom_task,
                "canonical_policy": policies.get(snip.check_id, ""),
            }
        )
    return cells


async def score_cells(
    cells: list[dict[str, Any]],
    *,
    model: str,
    concurrency: int = 8,
    refresh_llm: bool = False,
    judge_fn: JudgeFn | None = None,
) -> list[dict[str, Any]]:
    sem = asyncio.Semaphore(concurrency)

    async def one(cell: dict[str, Any]) -> dict[str, Any]:
        prev = cell.get("llm_assessment") or {}
        if (
            not refresh_llm
            and prev.get("clarity_grade")
            and prev.get("snippet_hash") == cell.get("snippet_hash")
            and prev.get("rubric_version") == RUBRIC_VERSION
        ):
            cell["status"] = "cached"
            return cell
        async with sem:
            try:
                scored = await assess_readability_llm(
                    check_id=cell["check_id"],
                    check_name=cell["check_name"],
                    check_description=cell["check_description"],
                    telecom_task=cell.get("telecom_task"),
                    framework=cell["framework"],
                    canonical_policy=cell["canonical_policy"],
                    snippet_text=cell["snippet_text"],
                    loc=cell["loc"],
                    model=model,
                    judge_fn=judge_fn,
                )
                cell["llm_assessment"] = {
                    "model": model,
                    "rubric_version": RUBRIC_VERSION,
                    "snippet_hash": cell["snippet_hash"],
                    "clarity_grade": scored.clarity_grade,
                    "rationale": scored.rationale,
                    "assessed_utc": datetime.now(UTC).isoformat(),
                }
                cell["status"] = "ok"
            except Exception as exc:
                cell["status"] = "llm_error"
                cell["llm_error"] = str(exc)
        return cell

    return list(await asyncio.gather(*[one(c) for c in cells]))


def merge_existing(cells: list[dict[str, Any]], existing: dict[str, dict]) -> list[dict[str, Any]]:
    for cell in cells:
        prev = existing.get(cell["key"], {})
        la = prev.get("llm_assessment") or {}
        if (
            la.get("clarity_grade")
            and la.get("snippet_hash") == cell.get("snippet_hash")
            and la.get("rubric_version") == RUBRIC_VERSION
        ):
            cell["llm_assessment"] = la
            cell["status"] = prev.get("status", "cached")
    return cells
