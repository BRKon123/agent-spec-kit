"""Shared failure-signature helpers for telecom study pipelines."""

from __future__ import annotations

import re
from typing import Any

from agent_spec_kit.generative import FailureSignature
from agent_spec_kit.runner import JobResult

_CHECK_KIND_RE = re.compile(r"^(\w+):")
_PATH_AT_RE = re.compile(
    r"(?:closest underlying mismatch was \(at |mismatch at )([^);\n]+)",
    re.I,
)
_FORBID_INDEX_RE = re.compile(r"found at index (\d+)", re.I)


def failure_signature_from_job(job: JobResult) -> FailureSignature | None:
    if job.counterexample is not None:
        return FailureSignature.from_counterexample(job.counterexample)
    if job.failure_kind:
        return FailureSignature(check_kind=job.failure_kind, path=None, assertion_id=None)
    return None


def failure_signature_from_display(
    detail: str,
    *,
    agent_turn_count: int | None = None,
    turn_count: int | None = None,
) -> FailureSignature | None:
    """Best-effort structural signature from stored ``failure_kind:detail`` text."""
    m = _CHECK_KIND_RE.match(detail)
    if not m:
        return None
    check_kind = m.group(1)
    path: str | None = None
    pm = _PATH_AT_RE.search(detail)
    if pm:
        path = pm.group(1).strip()
    elif check_kind == "forbid_tool_calls":
        im = _FORBID_INDEX_RE.search(detail)
        if im:
            path = f"$[{im.group(1)}]"
    elif check_kind in ("assert_output", "assert_that"):
        path = "$"

    turn_index: int | None = None
    if agent_turn_count is not None and agent_turn_count > 0:
        turn_index = agent_turn_count - 1
    elif turn_count is not None and turn_count > 0:
        turn_index = int(turn_count) - 1
    return FailureSignature(
        check_kind=check_kind,
        path=path,
        assertion_id=None,
        turn_index=turn_index,
    )


def failure_fields_from_signature(
    sig: FailureSignature | None,
    *,
    display: str | None,
) -> dict[str, Any]:
    struct = sig.as_dict() if sig is not None else None
    equiv = list(sig.equivalence_key()) if sig is not None else None
    return {
        "failure_signature": display,
        "failure_signature_struct": struct,
        "failure_equivalence_key": equiv,
    }


def failure_record_fields(job: JobResult) -> dict[str, Any]:
    """Display string plus structural equivalence fields for study records."""
    sig = failure_signature_from_job(job)
    display: str | None = None
    if not job.ok:
        detail = job.detail or job.failure_message or "failed"
        display = f"{job.failure_kind or job.status}:{detail}"
    return failure_fields_from_signature(sig, display=display)


def equivalence_key_from_record(record: dict[str, Any]) -> tuple[str | None, str | None, int | None] | None:
    ek = record.get("failure_equivalence_key")
    if ek is not None:
        return tuple(ek)
    struct = record.get("failure_signature_struct")
    if isinstance(struct, dict):
        sig = FailureSignature.from_dict(struct)
        return sig.equivalence_key() if sig is not None else None
    display = record.get("failure_signature")
    if isinstance(display, str) and display:
        sig = failure_signature_from_display(
            display,
            agent_turn_count=record.get("agent_turn_count"),
            turn_count=record.get("turn_count"),
        )
        return sig.equivalence_key() if sig is not None else None
    return None


def signatures_equivalent(
    left: FailureSignature | None,
    right: FailureSignature | None,
) -> bool:
    if left is None or right is None:
        return False
    return left.equivalence_key() == right.equivalence_key()


def classify_rerun_match(
    *,
    target: FailureSignature | None,
    observed: FailureSignature | None,
    job_ok: bool,
) -> str:
    if job_ok:
        return "passed"
    if target is None or observed is None:
        return "failed_other"
    if signatures_equivalent(target, observed):
        return "same_signature"
    if target.check_kind != observed.check_kind:
        return "different_check_kind"
    return "same_check_different_location"
