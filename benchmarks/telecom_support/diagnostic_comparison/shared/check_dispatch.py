"""Run real scenario checks against exported artifacts (shared by all framework ports)."""

from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path
from typing import Any

_BENCH = Path(__file__).resolve().parents[2]
if str(_BENCH) not in sys.path:
    sys.path.insert(0, str(_BENCH))

import os

from agent_spec_kit.match.api import check as match_check
from agent_spec_kit.match.api import coerce_any, forbidden_tool_calls_matcher
from agent_spec_kit.match.llm_criteria import LLMCriteriaMatcher
from agent_spec_kit.match.types import path_to_str
from agent_spec_kit.scenario_core import _coerce_tool_calls_list_spec
from scripts.diagnostic_quality_lib import FailureWitness
from store.snapshot import cleanup_store, load_store_from_snapshot
from tasks.specs import oracles as o

from diagnostic_comparison.shared.artifact_io import (
    matcher_error_from_witness_actual,
    tools_from_artifact,
)
from diagnostic_comparison.shared.slot_specs import (
    forbid_spec_for_slot,
    output_spec_for_slot,
    parse_forbid_names,
    trace_spec_for_slot,
)


class CheckFailed(Exception):
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


def _format_match_errors(errors: tuple) -> str:
    parts: list[str] = []
    for err in errors[:5]:
        parts.append(
            f"path={path_to_str(err.path)} code={err.code} "
            f"expected={err.expected!r} actual={err.actual!r} ({err.message})"
        )
    return " | ".join(parts)


def _state_oracle_fn(store: Any, witness: FailureWitness):
    msg = (witness.state_message or witness.expected or "").strip()
    if "expected zero credits" in msg:
        return lambda: o.assert_no_credit_rows(store)
    if "expected at least one audit note" in msg:
        return lambda: o.assert_audit_note_exists(store)
    if "expected at least one ticket" in msg:
        return lambda: o.assert_ticket_exists(store)
    if "expected no ticket on line" in msg:
        m = re.search(r"line '([^']+)'", msg)
        line = m.group(1) if m else o.stale_line_id(store)
        return lambda: o.assert_no_ticket_on_line(store, line)
    if "expected ticket for line" in msg:
        m = re.search(r"line '([^']+)'", msg)
        line = m.group(1) if m else str(store.seed_meta.get("line_id", ""))
        return lambda: o.assert_ticket_for_line(store, line)
    if "expected no sim order on line" in msg:
        m = re.search(r"line '([^']+)'", msg)
        line = m.group(1) if m else str(store.seed_meta.get("decoy_line_id", "LINE-WRONG"))
        return lambda: o.assert_no_sim_order_on_line(store, line)
    if "expected no get_customer_profile" in msg or "before auth" in msg:
        return lambda: o.assert_no_profile_read_before_auth(store)
    if "expected zero tickets" in msg:
        return lambda: o.assert_no_tickets(store)
    return None


def _run_state_check(store: Any, witness: FailureWitness) -> str:
    fn = _state_oracle_fn(store, witness)
    if fn is None:
        msg = (witness.state_message or witness.expected or "").strip()
        raise CheckFailed(f"no state oracle handler for: {msg[:120]}")
    try:
        fn()
    except AssertionError as exc:
        return str(exc).strip() or "AssertionError"
    raise CheckFailed("unexpected pass: state oracle satisfied")


def _run_trace_tool_calls(store: Any, artifact: dict[str, Any], witness: FailureWitness) -> None:
    tools = tools_from_artifact(artifact)
    if not tools:
        cached = matcher_error_from_witness_actual(
            str(artifact.get("witness_actual") or witness.actual or "")
        )
        if cached:
            raise CheckFailed(cached)
    spec = trace_spec_for_slot(artifact["family"], artifact["task"], store)
    if spec is None:
        raise CheckFailed("no trace spec for slot")
    list_spec = _coerce_tool_calls_list_spec(spec, ordered=True, allow_extras=True)
    result = match_check(list_spec, tools)
    if result.ok:
        raise CheckFailed("unexpected pass: tool_calls matched")
    raise CheckFailed(_format_match_errors(result.errors) or "tool_calls mismatch")


def _run_forbid_tool_calls(artifact: dict[str, Any], witness: FailureWitness) -> None:
    tools = tools_from_artifact(artifact)
    if not tools:
        cached = matcher_error_from_witness_actual(
            str(artifact.get("witness_actual") or witness.actual or "")
        )
        if cached:
            raise CheckFailed(cached)
    names = parse_forbid_names(witness.expected or "")
    if not names:
        spec = forbid_spec_for_slot(artifact["family"], artifact["task"])
        if spec is None:
            raise CheckFailed("no forbid spec for slot")
        forbid_spec = forbidden_tool_calls_matcher(spec, ordered=True)
    else:
        import agent_spec_kit.match as m

        forbid_spec = forbidden_tool_calls_matcher(
            [m.tool_call(n) for n in names],
            ordered=True,
        )
    result = match_check(forbid_spec, tools)
    if result.ok:
        raise CheckFailed("unexpected pass: no forbidden tool")
    raise CheckFailed(_format_match_errors(result.errors) or witness.expected or "forbidden tool present")


def _llm_failure_from_witness(artifact: dict[str, Any], witness: FailureWitness) -> str | None:
    """Reuse live-run LLM rubric text when offline re-judge is unavailable."""
    blob = str(artifact.get("witness_actual") or witness.actual or "").strip()
    if not blob:
        return None
    m = re.search(
        r"LLM criteria threshold failed:.*?(?=\n\n|\Z)",
        blob,
        re.DOTALL | re.IGNORECASE,
    )
    if m:
        return m.group(0).strip()
    if "Failed criteria:" in blob:
        idx = blob.find("Failed criteria:")
        prefix = blob[:idx].strip()
        tail = blob[idx:].strip()
        if "LLM criteria" in prefix:
            return f"{prefix}\n{tail}"
        return tail
    return None


def _run_output_check(artifact: dict[str, Any], witness: FailureWitness) -> None:
    output = str(artifact.get("final_output") or "")
    spec = output_spec_for_slot(artifact["family"], artifact["task"])
    if spec is None:
        raise CheckFailed("no output spec for slot")
    matcher = coerce_any(spec)
    if isinstance(matcher, LLMCriteriaMatcher) and not os.environ.get("OPENAI_API_KEY", "").strip():
        cached = _llm_failure_from_witness(artifact, witness)
        if cached:
            raise CheckFailed(cached)
        raise CheckFailed(
            "OPENAI_API_KEY required to re-run LLM output rubric offline "
            "(export witness_actual from fault log or set API key)"
        )
    if isinstance(matcher, LLMCriteriaMatcher):
        from agent_spec_kit.match.api import async_check

        try:
            result = asyncio.run(async_check(spec, output))
        except Exception as exc:
            name = type(exc).__name__
            if "OpenAI" in name or "api_key" in str(exc).lower():
                cached = _llm_failure_from_witness(artifact, witness)
                if cached:
                    raise CheckFailed(cached) from exc
            raise
    else:
        result = match_check(spec, output)
    if result.ok:
        raise CheckFailed("unexpected pass: output rubric passed")
    parts = [_format_match_errors(result.errors)]
    if witness.expected:
        parts.append(witness.expected)
    raise CheckFailed(" ".join(p for p in parts if p))


def run_core_check(artifact: dict[str, Any], witness: FailureWitness) -> str:
    """Run the failing check; return failure message (raises CheckFailed if check unexpectedly passes)."""
    snapshot = artifact.get("store_snapshot")
    if not snapshot:
        raise CheckFailed("artifact missing store_snapshot")
    store = load_store_from_snapshot(snapshot)
    try:
        check = witness.check or ""
        if check == "assert_that":
            return _run_state_check(store, witness)
        elif check == "assert_tool_calls":
            try:
                _run_trace_tool_calls(store, artifact, witness)
            except CheckFailed as exc:
                return exc.message
        elif check == "forbid_tool_calls":
            try:
                _run_forbid_tool_calls(artifact, witness)
            except CheckFailed as exc:
                return exc.message
        elif check == "assert_output":
            try:
                _run_output_check(artifact, witness)
            except CheckFailed as exc:
                return exc.message
        else:
            raise CheckFailed(f"unsupported check type: {check}")
    finally:
        cleanup_store(store)
    return "unexpected pass"
