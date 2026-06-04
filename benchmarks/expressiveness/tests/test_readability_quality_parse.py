"""Tests for combined authoring-clarity LLM rubric and mocked judge."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

_EXPR = Path(__file__).resolve().parents[1]
if str(_EXPR) not in sys.path:
    sys.path.insert(0, str(_EXPR))

from scripts.readability_quality_lib import (
    AUTHORING_CLARITY_RUBRIC,
    ClarityAssessment,
    _build_judge_user_prompt,
    assess_readability_llm,
    load_canonical_policies,
    normalize_grade,
)


def test_normalize_grade_valid():
    assert normalize_grade("a") == "A"
    assert normalize_grade(" B ") == "B"


def test_normalize_grade_rejects_e_and_numeric():
    with pytest.raises(ValueError):
        normalize_grade("E")
    with pytest.raises(ValueError):
        normalize_grade("3")


def test_load_canonical_policies():
    policies = load_canonical_policies()
    assert "C05" in policies
    assert "authenticate_customer" in policies["C05"]


def test_build_judge_user_prompt_includes_combined_rubric():
    user = _build_judge_user_prompt(
        check_id="C05",
        check_name="Ordered tool-call sequence",
        check_description="Tools occur in policy order.",
        telecom_task="T02",
        framework="pytest_plain",
        canonical_policy="Root tools contain subsequence authenticate_customer → get_outage_status.",
        snippet_text="assert ok",
        loc=3,
    )
    assert "Immediate grasp" in user
    assert "Scenario shape" in user
    assert "Surface form" in user
    assert "reading cost" in user.lower()
    assert "Calibration" in user
    assert "strict" in user.lower()
    assert "LangSmith" not in user
    assert "C05" in user
    assert "clarity_grade" in user


def test_assess_readability_llm_mock():
    async def mock_judge(**kwargs: object) -> ClarityAssessment:
        return ClarityAssessment(clarity_grade="B", rationale="fixture")

    scored = asyncio.run(
        assess_readability_llm(
            check_id="C06",
            check_name="Forbidden tool-call",
            check_description="Unsafe tools must not appear.",
            telecom_task="T49",
            framework="langsmith",
            canonical_policy="Root tools must not include apply_bill_credit.",
            snippet_text="return {'key': 'forbidden_tools', 'score': 0}",
            loc=1,
            judge_fn=mock_judge,
        )
    )
    assert scored.clarity_grade == "B"


def test_clarity_assessment_rejects_e():
    with pytest.raises(Exception):
        ClarityAssessment(clarity_grade="E", rationale="bad")
