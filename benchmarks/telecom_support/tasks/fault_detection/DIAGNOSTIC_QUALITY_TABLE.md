# Diagnostic quality table

- Generated: 2026-05-27T11:13:28.322020+00:00
- Records: `tasks/fault_detection/diagnostic_records.json`
- LLM model: `openai:gpt-5-nano`
- Cells scored OK: `158` / `158`

Regenerate:

```bash
cd benchmarks/telecom_support
uv run python scripts/collect_diagnostic_failures.py
OPENAI_API_KEY=... uv run python scripts/extract_diagnostic_quality.py
uv run python scripts/generate_diagnostic_quality_table.py
```

## Specificity rubric (0–4)

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


## Section A — Oracle diagnostic ceiling (agent_spec_kit)

For F-detected tasks, failures under O/S/T/F oracles.

| Case | Oracle | Specificity | Failed req? | Trace/state? | Path? | E vs A? | Nodes | LOC |
|------|--------|------------:|:-----------:|:------------:|:-----:|:-------:|------:|----:|
| F01/T44 | T | 4 | Yes | Yes | Yes | Yes | 1 | 0 |
| F02/T29 | S | 4 | Yes | Yes | No | Yes | 1 | 0 |
| F02/T29 | T | 4 | Yes | Yes | Yes | Yes | 1 | 0 |
| F02/T43 | S | 4 | Yes | Yes | No | Yes | 1 | 0 |
| F02/T46 | S | 4 | Yes | Yes | No | Yes | 1 | 0 |
| F02/T46 | T | 4 | Yes | Yes | Yes | Yes | 1 | 0 |
| F03/T17 | S | 3 | Yes | Yes | No | Yes | 1 | 0 |
| F03/T27 | S | 3 | Yes | Yes | No | Yes | 1 | 0 |
| F04/T45 | S | 4 | No | Yes | No | Yes | 1 | 0 |
| F04/T49 | S | 3 | Yes | Yes | Yes | Yes | 1 | 0 |
| F04/T50 | O | 4 | Yes | Yes | No | Yes | 1 | 0 |
| F04/T50 | S | 4 | Yes | Yes | No | Yes | 1 | 0 |
| F05/T38 | T | 4 | Yes | Yes | Yes | Yes | 1 | 0 |
| F07/T29 | T | 4 | Yes | Yes | Yes | Yes | 1 | 0 |
| F07/T30 | O | 4 | Yes | Yes | No | Yes | 1 | 0 |
| F07/T30 | T | 4 | Yes | Yes | Yes | Yes | 1 | 0 |
| F07/T42 | O | 4 | Yes | Yes | No | Yes | 1 | 0 |
| F07/T42 | S | 4 | Yes | Yes | No | Yes | 1 | 0 |
| F07/T42 | T | 4 | Yes | Yes | Yes | Yes | 1 | 0 |
| F07/T43 | S | 4 | Yes | Yes | Yes | Yes | 1 | 0 |
| F07/T43 | T | 4 | Yes | Yes | Yes | Yes | 1 | 0 |
| F08/T21 | S | 3 | Yes | Yes | No | Yes | 1 | 0 |
| F08/T21 | T | 3 | Yes | Yes | No | Yes | 1 | 0 |
| F09/T04 | O | 4 | Yes | Yes | No | Yes | 1 | 0 |
| F09/T04 | S | 3 | Yes | Yes | Yes | Yes | 1 | 0 |
| F09/T04 | T | 3 | Yes | Yes | No | Yes | 1 | 0 |
| F09/T19 | O | 3 | Yes | Yes | No | Yes | 1 | 0 |
| F09/T19 | S | 3 | Yes | Yes | No | Yes | 1 | 0 |
| F09/T19 | T | 3 | Yes | Yes | No | Yes | 1 | 0 |
| F10/T29 | T | 4 | Yes | Yes | Yes | Yes | 1 | 0 |
| F10/T43 | O | 4 | Yes | Yes | Yes | Yes | 1 | 0 |
| F10/T44 | T | 4 | Yes | Yes | Yes | Yes | 1 | 0 |

## Section B — Main table (detected, full oracle, six frameworks)

| Case | Framework | Specificity | Failed req? | Trace/state? | Path? | E vs A? | Nodes | LOC |
|------|-----------|------------:|:-----------:|:------------:|:-----:|:-------:|------:|----:|
| F01/T44 | agent_spec_kit | 4 | Yes | Yes | Yes | Yes | 1 | 0 |
| F01/T44 | braintrust | 4 | Yes | No | No | Yes | 1 | 24 |
| F01/T44 | langsmith | 4 | Yes | Yes | No | Yes | 1 | 24 |
| F01/T44 | promptfoo | 3 | No | No | No | Yes | 1 | 32 |
| F01/T44 | pydantic_evals | 3 | Yes | No | No | Yes | 1 | 18 |
| F01/T44 | pytest_plain | 3 | Yes | No | No | Yes | 1 | 18 |
| F02/T29 | agent_spec_kit | 4 | Yes | Yes | Yes | Yes | 1 | 0 |
| F02/T29 | braintrust | 4 | Yes | No | Yes | Yes | 1 | 26 |
| F02/T29 | langsmith | 3 | No | No | Yes | Yes | 1 | 26 |
| F02/T29 | promptfoo | 4 | No | No | Yes | No | 0 | 34 |
| F02/T29 | pydantic_evals | 4 | Yes | No | Yes | Yes | 0 | 20 |
| F02/T29 | pytest_plain | 4 | Yes | No | Yes | No | 0 | 20 |
| F02/T43 | agent_spec_kit | 4 | Yes | Yes | Yes | Yes | 1 | 0 |
| F02/T43 | braintrust | 3 | Yes | No | No | Yes | 0 | 30 |
| F02/T43 | langsmith | 4 | Yes | No | No | Yes | 0 | 30 |
| F02/T43 | promptfoo | 3 | No | No | No | Yes | 0 | 40 |
| F02/T43 | pydantic_evals | 4 | Yes | No | No | Yes | 0 | 24 |
| F02/T43 | pytest_plain | 3 | Yes | Yes | No | Yes | 0 | 24 |
| F02/T46 | agent_spec_kit | 4 | Yes | Yes | Yes | Yes | 1 | 0 |
| F02/T46 | braintrust | 3 | Yes | No | No | No | 1 | 34 |
| F02/T46 | langsmith | 3 | Yes | No | Yes | No | 1 | 34 |
| F02/T46 | promptfoo | 3 | No | No | No | No | 0 | 43 |
| F02/T46 | pydantic_evals | 3 | Yes | No | Yes | No | 0 | 28 |
| F02/T46 | pytest_plain | 2 | Yes | No | Yes | No | 0 | 28 |
| F03/T17 | agent_spec_kit | 3 | Yes | Yes | No | Yes | 1 | 0 |
| F03/T17 | braintrust | 3 | Yes | No | No | Yes | 0 | 29 |
| F03/T17 | langsmith | 3 | Yes | No | No | Yes | 0 | 29 |
| F03/T17 | promptfoo | 2 | No | No | No | Yes | 0 | 39 |
| F03/T17 | pydantic_evals | 3 | Yes | No | No | Yes | 0 | 23 |
| F03/T17 | pytest_plain | 3 | Yes | No | No | Yes | 0 | 23 |
| F03/T27 | agent_spec_kit | 3 | Yes | Yes | No | Yes | 1 | 0 |
| F03/T27 | braintrust | 3 | Yes | No | No | Yes | 0 | 29 |
| F03/T27 | langsmith | 3 | Yes | No | No | Yes | 0 | 29 |
| F03/T27 | promptfoo | 3 | No | No | No | Yes | 0 | 39 |
| F03/T27 | pydantic_evals | 2 | Yes | No | No | Yes | 0 | 23 |
| F03/T27 | pytest_plain | 3 | Yes | No | No | Yes | 0 | 23 |
| F04/T45 | agent_spec_kit | 4 | Yes | Yes | No | Yes | 1 | 0 |
| F04/T45 | braintrust | 3 | Yes | No | No | No | 0 | 29 |
| F04/T45 | langsmith | 3 | Yes | No | No | No | 0 | 29 |
| F04/T45 | promptfoo | 4 | No | No | No | Yes | 0 | 39 |
| F04/T45 | pydantic_evals | 4 | Yes | No | No | Yes | 0 | 23 |
| F04/T45 | pytest_plain | 4 | Yes | Yes | No | No | 0 | 23 |
| F04/T49 | agent_spec_kit | 4 | Yes | Yes | No | Yes | 1 | 0 |
| F04/T49 | braintrust | 4 | Yes | No | No | Yes | 0 | 29 |
| F04/T49 | langsmith | 3 | Yes | No | No | Yes | 0 | 29 |
| F04/T49 | promptfoo | 3 | No | No | No | No | 0 | 39 |
| F04/T49 | pydantic_evals | 4 | Yes | No | No | Yes | 0 | 23 |
| F04/T49 | pytest_plain | 2 | Yes | No | Yes | No | 0 | 23 |
| F04/T50 | agent_spec_kit | 4 | Yes | Yes | No | Yes | 1 | 0 |
| F04/T50 | braintrust | 4 | Yes | No | No | No | 0 | 23 |
| F04/T50 | langsmith | 4 | Yes | No | No | No | 0 | 23 |
| F04/T50 | promptfoo | 4 | No | No | No | No | 0 | 31 |
| F04/T50 | pydantic_evals | 3 | Yes | No | No | No | 0 | 17 |
| F04/T50 | pytest_plain | 4 | Yes | No | No | No | 0 | 17 |
| F05/T38 | agent_spec_kit | 3 | Yes | Yes | Yes | No | 1 | 0 |
| F05/T38 | braintrust | 4 | Yes | No | No | No | 1 | 24 |
| F05/T38 | langsmith | 3 | Yes | No | No | No | 1 | 24 |
| F05/T38 | promptfoo | 2 | No | No | No | No | 1 | 32 |
| F05/T38 | pydantic_evals | 2 | Yes | Yes | No | No | 1 | 18 |
| F05/T38 | pytest_plain | 2 | Yes | Yes | No | No | 1 | 18 |
| F07/T29 | agent_spec_kit | 4 | Yes | Yes | Yes | Yes | 1 | 0 |
| F07/T29 | braintrust | 4 | Yes | Yes | No | No | 1 | 21 |
| F07/T29 | langsmith | 4 | Yes | Yes | No | No | 1 | 21 |
| F07/T29 | promptfoo | 3 | Yes | Yes | No | No | 1 | 29 |
| F07/T29 | pydantic_evals | 4 | Yes | Yes | No | No | 1 | 15 |
| F07/T29 | pytest_plain | 3 | Yes | Yes | No | No | 1 | 15 |
| F07/T30 | agent_spec_kit | 4 | Yes | Yes | Yes | Yes | 1 | 0 |
| F07/T30 | braintrust | 3 | Yes | Yes | No | No | 1 | 21 |
| F07/T30 | langsmith | 4 | Yes | Yes | No | No | 1 | 21 |
| F07/T30 | promptfoo | 3 | Yes | Yes | No | No | 1 | 29 |
| F07/T30 | pydantic_evals | 4 | Yes | Yes | No | No | 1 | 15 |
| F07/T30 | pytest_plain | 4 | Yes | Yes | No | No | 1 | 15 |
| F07/T42 | agent_spec_kit | 4 | Yes | Yes | Yes | Yes | 1 | 0 |
| F07/T42 | braintrust | 4 | Yes | Yes | No | No | 1 | 21 |
| F07/T42 | langsmith | 4 | Yes | Yes | No | No | 1 | 21 |
| F07/T42 | promptfoo | 3 | Yes | Yes | No | No | 1 | 29 |
| F07/T42 | pydantic_evals | 3 | Yes | Yes | No | No | 1 | 15 |
| F07/T42 | pytest_plain | 3 | Yes | Yes | No | No | 1 | 15 |
| F07/T43 | agent_spec_kit | 4 | Yes | Yes | Yes | Yes | 1 | 0 |
| F07/T43 | braintrust | 3 | Yes | Yes | No | No | 1 | 21 |
| F07/T43 | langsmith | 4 | Yes | Yes | No | No | 1 | 21 |
| F07/T43 | promptfoo | 3 | Yes | Yes | No | No | 1 | 29 |
| F07/T43 | pydantic_evals | 3 | Yes | Yes | No | No | 1 | 15 |
| F07/T43 | pytest_plain | 4 | Yes | Yes | No | No | 1 | 15 |
| F08/T21 | agent_spec_kit | 4 | Yes | Yes | Yes | Yes | 1 | 0 |
| F08/T21 | braintrust | 3 | Yes | No | No | No | 0 | 29 |
| F08/T21 | langsmith | 3 | Yes | No | No | No | 0 | 29 |
| F08/T21 | promptfoo | 2 | No | No | No | No | 0 | 39 |
| F08/T21 | pydantic_evals | 3 | Yes | No | No | No | 0 | 23 |
| F08/T21 | pytest_plain | 1 | Yes | No | No | No | 0 | 23 |
| F09/T04 | agent_spec_kit | 3 | Yes | Yes | No | Yes | 1 | 0 |
| F09/T04 | braintrust | 3 | Yes | No | No | No | 0 | 29 |
| F09/T04 | langsmith | 3 | Yes | No | No | No | 0 | 29 |
| F09/T04 | promptfoo | 3 | No | No | No | No | 0 | 39 |
| F09/T04 | pydantic_evals | 1 | Yes | No | No | No | 0 | 23 |
| F09/T04 | pytest_plain | 2 | Yes | No | No | No | 0 | 23 |
| F09/T19 | agent_spec_kit | 4 | Yes | Yes | No | Yes | 1 | 0 |
| F09/T19 | braintrust | 3 | Yes | No | No | No | 0 | 29 |
| F09/T19 | langsmith | 3 | Yes | No | No | No | 0 | 29 |
| F09/T19 | promptfoo | 3 | No | No | No | No | 0 | 39 |
| F09/T19 | pydantic_evals | 1 | Yes | No | No | No | 0 | 23 |
| F09/T19 | pytest_plain | 1 | Yes | No | No | No | 0 | 23 |
| F10/T29 | agent_spec_kit | 4 | Yes | Yes | Yes | Yes | 1 | 0 |
| F10/T29 | braintrust | 4 | Yes | No | Yes | No | 1 | 26 |
| F10/T29 | langsmith | 4 | Yes | No | Yes | Yes | 1 | 26 |
| F10/T29 | promptfoo | 4 | No | No | Yes | No | 0 | 34 |
| F10/T29 | pydantic_evals | 4 | Yes | No | Yes | No | 0 | 20 |
| F10/T29 | pytest_plain | 4 | Yes | No | Yes | No | 0 | 20 |
| F10/T42 | agent_spec_kit | 3 | Yes | Yes | No | Yes | 1 | 0 |
| F10/T42 | braintrust | 3 | Yes | No | No | Yes | 0 | 29 |
| F10/T42 | langsmith | 3 | Yes | No | No | Yes | 0 | 29 |
| F10/T42 | promptfoo | 3 | No | No | No | Yes | 0 | 39 |
| F10/T42 | pydantic_evals | 3 | Yes | No | No | Yes | 0 | 23 |
| F10/T42 | pytest_plain | 3 | Yes | No | No | Yes | 0 | 23 |
| F10/T43 | agent_spec_kit | 4 | Yes | Yes | No | Yes | 1 | 0 |
| F10/T43 | braintrust | 4 | No | No | No | Yes | 0 | 25 |
| F10/T43 | langsmith | 4 | Yes | No | No | Yes | 0 | 25 |
| F10/T43 | promptfoo | 3 | No | No | No | Yes | 0 | 33 |
| F10/T43 | pydantic_evals | 4 | Yes | No | No | Yes | 0 | 19 |
| F10/T43 | pytest_plain | 3 | Yes | No | No | Yes | 0 | 19 |
| F10/T44 | agent_spec_kit | 4 | Yes | Yes | Yes | Yes | 1 | 0 |
| F10/T44 | braintrust | 4 | No | No | No | Yes | 1 | 24 |
| F10/T44 | langsmith | 4 | Yes | No | No | Yes | 1 | 24 |
| F10/T44 | promptfoo | 4 | No | Yes | No | Yes | 1 | 32 |
| F10/T44 | pydantic_evals | 4 | Yes | No | No | Yes | 1 | 18 |
| F10/T44 | pytest_plain | 4 | Yes | No | No | Yes | 1 | 18 |

## Section C — Qualitative examples

Configure slots in `diagnostic_exemplars.yaml` to render side-by-side snippets here.

## Conclusion (template)

Richer oracles and frameworks that surface trace, state, and matcher witnesses produce more localised failure messages. Output-only or generic assertion shells tend toward lower specificity scores on the same underlying faults.
