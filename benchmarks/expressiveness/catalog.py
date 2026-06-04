"""Twelve check-type specimens for the expressiveness comparison harness."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CheckId = Literal[
    "C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09", "C10", "C11", "C12"
]


@dataclass(frozen=True, slots=True)
class CheckSpecimen:
    check_id: CheckId
    name: str
    description: str
    telecom_seed: str | None
    telecom_task: str | None
    needs_llm: bool
    needs_live_store: bool


SPECIMENS: tuple[CheckSpecimen, ...] = (
    CheckSpecimen(
        "C01",
        "Final output semantic/rubric",
        "Final answer satisfies natural-language criteria.",
        "task_T16",
        "T16",
        False,
        False,
    ),
    CheckSpecimen(
        "C02",
        "Structured object shape",
        "Tool JSON has required fields, types, and no forbidden extras.",
        "task_T09",
        "T09",
        False,
        False,
    ),
    CheckSpecimen(
        "C03",
        "Conditional structured object rule",
        "Fields required/forbidden depending on another field value.",
        None,
        "nested_example",
        False,
        False,
    ),
    CheckSpecimen(
        "C04",
        "Numeric/range/regex field constraint",
        "Fields match numeric bounds or regex patterns.",
        "task_T23",
        "T23",
        False,
        False,
    ),
    CheckSpecimen(
        "C05",
        "Ordered tool-call sequence",
        "Tools occur in policy order with extras allowed.",
        "task_T02",
        "T02",
        False,
        False,
    ),
    CheckSpecimen(
        "C06",
        "Forbidden tool-call",
        "Unsafe tools must not appear while other tools may.",
        "task_T49",
        "T49",
        False,
        False,
    ),
    CheckSpecimen(
        "C07",
        "Tool argument matching",
        "Tool args match expected structure from conversation state.",
        "task_T01",
        "T01",
        False,
        False,
    ),
    CheckSpecimen(
        "C08",
        "Tool result matching",
        "Specialist result satisfies structure or LLM rubric.",
        "task_T10",
        "T10",
        True,
        False,
    ),
    CheckSpecimen(
        "C09",
        "Nested tool-call matching",
        "Specialist internally calls child tools in order.",
        "task_T40",
        "T40",
        False,
        False,
    ),
    CheckSpecimen(
        "C10",
        "Unordered sibling tool matching",
        "Independent tools both called regardless of order.",
        "task_T06",
        "T06",
        False,
        False,
    ),
    CheckSpecimen(
        "C11",
        "Environment/final-state assertion",
        "External DB state matches expected mutations.",
        "task_T04",
        "T04",
        False,
        True,
    ),
    CheckSpecimen(
        "C12",
        "Multi-turn conversation/state-memory",
        "Agent uses corrected facts from later turns.",
        "task_T46",
        "T46",
        False,
        True,
    ),
)

SPECIMEN_BY_ID: dict[CheckId, CheckSpecimen] = {s.check_id: s for s in SPECIMENS}

# Table cell ratings: first-class | built-in+config | custom scorer | harness glue
FRAMEWORK_RATINGS: dict[str, dict[CheckId, str]] = {
    "agent_spec_kit": {
        "C01": "First-class",
        "C02": "First-class",
        "C03": "First-class",
        "C04": "First-class",
        "C05": "First-class",
        "C06": "First-class",
        "C07": "First-class",
        "C08": "First-class",
        "C09": "First-class",
        "C10": "First-class",
        "C11": "First-class",
        "C12": "First-class",
    },
    "pytest_plain": {
        "C01": "Custom code",
        "C02": "Custom code",
        "C03": "Custom code",
        "C04": "Custom code",
        "C05": "Custom code",
        "C06": "Custom code",
        "C07": "Custom code",
        "C08": "Custom code",
        "C09": "Custom code",
        "C10": "Custom code",
        "C11": "Custom code",
        "C12": "Custom code",
    },
    "langsmith": {
        "C01": "Custom code evaluator",
        "C02": "Custom code evaluator",
        "C03": "Custom code evaluator",
        "C04": "Custom code evaluator",
        "C05": "Custom code evaluator",
        "C06": "Custom code evaluator",
        "C07": "Custom code evaluator",
        "C08": "Custom code evaluator",
        "C09": "Custom code evaluator",
        "C10": "Custom code evaluator",
        "C11": "Custom code evaluator",
        "C12": "Custom code evaluator",
    },
    "pydantic_evals": {
        "C01": "Custom evaluator",
        "C02": "Custom evaluator",
        "C03": "Custom evaluator",
        "C04": "Custom evaluator",
        "C05": "Custom evaluator",
        "C06": "Custom evaluator",
        "C07": "Custom evaluator",
        "C08": "Custom evaluator",
        "C09": "Custom evaluator",
        "C10": "Custom evaluator",
        "C11": "Custom evaluator",
        "C12": "Custom evaluator",
    },
    "promptfoo": {
        "C01": "Custom assertion",
        "C02": "Custom assertion",
        "C03": "Custom assertion",
        "C04": "Custom assertion",
        "C05": "Custom assertion",
        "C06": "Custom assertion",
        "C07": "Custom assertion",
        "C08": "Custom assertion",
        "C09": "Custom assertion",
        "C10": "Custom assertion",
        "C11": "Custom assertion",
        "C12": "Custom assertion",
    },
    "braintrust": {
        "C01": "Code scorer",
        "C02": "Code scorer",
        "C03": "Code scorer",
        "C04": "Code scorer",
        "C05": "Code scorer",
        "C06": "Code scorer",
        "C07": "Code scorer",
        "C08": "Code scorer",
        "C09": "Code scorer",
        "C10": "Code scorer",
        "C11": "Code scorer",
        "C12": "Code scorer",
    },
}

# Qualitative grade when a check fails on an intentional negative fixture (see failures_samples.yaml).
FAILURE_SPECIFICITY_GRADES: dict[str, str] = {
    "A": "Exact JSON/path witness with expected vs actual (e.g. matcher counterexample at `result.severity`)",
    "B": "Names the violated rule, tool, or arg/result slice in plain text (no structured path)",
    "C": "Named evaluator/scorer key or check category only (e.g. score 0 dict), no tool/field witness",
    "D": "Generic assertion or scorer failure (e.g. `AssertionError`, `score 0`, validation error class)",
    "E": "Opaque pass/fail boolean with no diagnostic detail",
}

# Same order as LOC column in EXPRESSIVENESS_TABLE.md.
FRAMEWORK_LOC_ABBREVS: tuple[tuple[str, str], ...] = (
    ("agent_spec_kit", "ask"),
    ("pytest_plain", "py"),
    ("langsmith", "ls"),
    ("pydantic_evals", "pe"),
    ("promptfoo", "pf"),
    ("braintrust", "bt"),
)

# Manually graded from captured messages — see MANUAL_FAILURE_CLASSIFICATION.md.
# Bare ``AssertionError`` (empty) is D. Evaluator dict with only key + score:0 is C, not B.
FAILURE_SPECIFICITY: dict[CheckId, dict[str, str]] = {
    "C01": {
        "agent_spec_kit": "A",
        "pytest_plain": "D",
        "langsmith": "B",
        "pydantic_evals": "B",
        "promptfoo": "B",
        "braintrust": "B",
    },
    "C02": {
        "agent_spec_kit": "A",
        "pytest_plain": "D",
        "langsmith": "B",
        "pydantic_evals": "B",
        "promptfoo": "B",
        "braintrust": "B",
    },
    "C03": {
        "agent_spec_kit": "A",
        "pytest_plain": "D",
        "langsmith": "B",
        "pydantic_evals": "B",
        "promptfoo": "B",
        "braintrust": "B",
    },
    "C04": {
        "agent_spec_kit": "A",
        "pytest_plain": "D",
        "langsmith": "B",
        "pydantic_evals": "B",
        "promptfoo": "B",
        "braintrust": "B",
    },
    "C05": {
        "agent_spec_kit": "A",
        "pytest_plain": "D",
        "langsmith": "B",
        "pydantic_evals": "B",
        "promptfoo": "B",
        "braintrust": "B",
    },
    "C06": {
        "agent_spec_kit": "A",
        "pytest_plain": "D",
        "langsmith": "C",
        "pydantic_evals": "B",
        "promptfoo": "B",
        "braintrust": "C",
    },
    "C07": {
        "agent_spec_kit": "A",
        "pytest_plain": "B",
        "langsmith": "B",
        "pydantic_evals": "B",
        "promptfoo": "B",
        "braintrust": "B",
    },
    "C08": {
        "agent_spec_kit": "A",
        "pytest_plain": "D",
        "langsmith": "B",
        "pydantic_evals": "B",
        "promptfoo": "B",
        "braintrust": "B",
    },
    "C09": {
        "agent_spec_kit": "A",
        "pytest_plain": "D",
        "langsmith": "B",
        "pydantic_evals": "B",
        "promptfoo": "B",
        "braintrust": "B",
    },
    "C10": {
        "agent_spec_kit": "A",
        "pytest_plain": "D",
        "langsmith": "B",
        "pydantic_evals": "B",
        "promptfoo": "B",
        "braintrust": "B",
    },
    "C11": {
        "agent_spec_kit": "B",
        "pytest_plain": "B",
        "langsmith": "B",
        "pydantic_evals": "B",
        "promptfoo": "B",
        "braintrust": "B",
    },
    "C12": {
        "agent_spec_kit": "A",
        "pytest_plain": "D",
        "langsmith": "B",
        "pydantic_evals": "B",
        "promptfoo": "B",
        "braintrust": "B",
    },
}
