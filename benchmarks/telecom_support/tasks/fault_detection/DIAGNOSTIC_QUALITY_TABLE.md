# Diagnostic quality table

- Generated: 2026-06-06T10:57:47.311808+00:00
- Records: `tasks/fault_detection/diagnostic_records.json`
- LLM model: `openai:gpt-5-nano`
- Cells scored OK: `200` / `200`

Regenerate:

```bash
cd benchmarks/telecom_support
uv run python scripts/collect_diagnostic_failures.py
OPENAI_API_KEY=... uv run python scripts/extract_diagnostic_quality.py
uv run python scripts/generate_diagnostic_quality_table.py
uv run python scripts/generate_diagnostic_latex.py
```

## Specificity rubric (A–E)

| Grade | Meaning (failure message only; A best, E worst) |
| --- | --- |
| **A** | Exact location in the trace or store plus expected vs actual (e.g. matcher counterexample with path and values). |
| **B** | Names the broken rule, tool, or field in plain text without a structured path witness. |
| **C** | Says which check or scorer failed (evaluator key and `score: 0`) but not which tool, field, or values. |
| **D** | Generic failure shell: bare `AssertionError`, empty assert, or validation class only. |
| **E** | Opaque pass/fail with almost no diagnostic detail. |

Do not award higher grades for extraction hooks, replay IDs, or signature stability. A scorer dict with only `key` and `score: 0` is typically **C**, not **D**.


## Section A — Oracle diagnostic ceiling (agent_spec_kit)

For F-detected tasks, failures under O/S/T/F oracles.

| Case | Oracle | Grade | Failed req? | Where? | Path? | E vs A? | LOC |
|------|--------|:-----:|:-----------:|:------:|:-----:|:-------:|----:|
| F01/T44 | T | A | Yes | Yes | Yes | Yes | 0 |
| F02/T29 | S | A | Yes | Yes | No | Yes | 0 |
| F02/T29 | T | A | Yes | Yes | Yes | Yes | 0 |
| F02/T43 | S | A | Yes | Yes | No | Yes | 0 |
| F02/T46 | S | A | Yes | Yes | No | Yes | 0 |
| F02/T46 | T | A | Yes | Yes | Yes | Yes | 0 |
| F03/T17 | S | A | Yes | Yes | No | Yes | 0 |
| F03/T27 | S | A | Yes | Yes | Yes | Yes | 0 |
| F04/T45 | S | A | Yes | Yes | No | Yes | 0 |
| F04/T49 | S | B | Yes | Yes | No | Yes | 0 |
| F04/T50 | O | A | Yes | Yes | Yes | Yes | 0 |
| F04/T50 | S | A | Yes | Yes | No | Yes | 0 |
| F05/T38 | T | A | Yes | Yes | Yes | Yes | 0 |
| F07/T29 | T | A | Yes | Yes | Yes | Yes | 0 |
| F07/T30 | O | A | Yes | Yes | No | Yes | 0 |
| F07/T30 | T | A | Yes | Yes | Yes | Yes | 0 |
| F07/T42 | O | A | Yes | Yes | No | Yes | 0 |
| F07/T42 | S | A | Yes | Yes | No | Yes | 0 |
| F07/T42 | T | A | Yes | Yes | Yes | Yes | 0 |
| F07/T43 | S | A | Yes | Yes | No | Yes | 0 |
| F07/T43 | T | A | Yes | Yes | Yes | Yes | 0 |
| F08/T21 | S | B | Yes | Yes | No | Yes | 0 |
| F08/T21 | T | B | Yes | Yes | No | Yes | 0 |
| F09/T04 | O | B | Yes | Yes | No | Yes | 0 |
| F09/T04 | S | B | Yes | Yes | No | Yes | 0 |
| F09/T04 | T | B | Yes | Yes | No | Yes | 0 |
| F09/T19 | O | B | Yes | Yes | No | Yes | 0 |
| F09/T19 | S | B | Yes | Yes | No | Yes | 0 |
| F09/T19 | T | B | Yes | Yes | No | Yes | 0 |
| F10/T29 | T | A | Yes | Yes | Yes | Yes | 0 |
| F10/T43 | O | A | Yes | Yes | No | Yes | 0 |
| F10/T44 | T | A | Yes | Yes | Yes | Yes | 0 |

## Section B — Main table (detected, full oracle, eight frameworks)

| Case | Framework | Grade | Failed req? | Where? | Path? | E vs A? | LOC |
|------|-----------|:-----:|:-----------:|:------:|:-----:|:-------:|----:|
| F01/T44 | ask | A | Yes | Yes | Yes | Yes | 0 |
| F01/T44 | bt | A | Yes | Yes | No | Yes | 24 |
| F01/T44 | de | B | Yes | No | No | Yes | 14 |
| F01/T44 | ls | B | Yes | No | No | Yes | 24 |
| F01/T44 | pf | A | No | No | No | Yes | 32 |
| F01/T44 | pe | B | Yes | Yes | No | Yes | 18 |
| F01/T44 | py | A | Yes | Yes | No | Yes | 18 |
| F01/T44 | rg | B | Yes | No | No | Yes | 14 |
| F02/T29 | ask | A | Yes | Yes | Yes | Yes | 0 |
| F02/T29 | bt | B | Yes | No | Yes | Yes | 26 |
| F02/T29 | de | A | Yes | No | No | Yes | 14 |
| F02/T29 | ls | A | Yes | No | Yes | Yes | 26 |
| F02/T29 | pf | B | No | No | Yes | Yes | 34 |
| F02/T29 | pe | A | Yes | No | Yes | Yes | 20 |
| F02/T29 | py | B | Yes | No | Yes | Yes | 20 |
| F02/T29 | rg | B | Yes | No | Yes | Yes | 14 |
| F02/T43 | ask | B | Yes | Yes | Yes | Yes | 0 |
| F02/T43 | bt | A | Yes | No | No | Yes | 30 |
| F02/T43 | de | A | Yes | No | No | Yes | 14 |
| F02/T43 | ls | A | Yes | No | No | Yes | 30 |
| F02/T43 | pf | A | No | No | No | Yes | 40 |
| F02/T43 | pe | A | Yes | No | No | Yes | 24 |
| F02/T43 | py | A | Yes | No | No | Yes | 24 |
| F02/T43 | rg | A | Yes | No | No | Yes | 14 |
| F02/T46 | ask | A | Yes | Yes | Yes | Yes | 0 |
| F02/T46 | bt | B | Yes | No | Yes | No | 34 |
| F02/T46 | de | A | Yes | No | Yes | No | 14 |
| F02/T46 | ls | B | Yes | No | No | No | 34 |
| F02/T46 | pf | B | No | No | No | No | 43 |
| F02/T46 | pe | B | Yes | No | Yes | No | 28 |
| F02/T46 | py | B | Yes | No | Yes | No | 28 |
| F02/T46 | rg | B | Yes | No | Yes | No | 14 |
| F03/T17 | ask | A | Yes | Yes | No | Yes | 0 |
| F03/T17 | bt | A | Yes | No | No | Yes | 29 |
| F03/T17 | de | B | Yes | No | No | Yes | 14 |
| F03/T17 | ls | B | Yes | No | No | Yes | 29 |
| F03/T17 | pf | B | No | No | No | Yes | 39 |
| F03/T17 | pe | B | Yes | No | No | Yes | 23 |
| F03/T17 | py | C | Yes | No | No | Yes | 23 |
| F03/T17 | rg | E | Yes | No | No | Yes | 14 |
| F03/T27 | ask | A | Yes | Yes | No | Yes | 0 |
| F03/T27 | bt | B | Yes | No | No | Yes | 29 |
| F03/T27 | de | B | Yes | No | No | Yes | 14 |
| F03/T27 | ls | A | Yes | No | No | Yes | 29 |
| F03/T27 | pf | C | No | No | No | Yes | 39 |
| F03/T27 | pe | E | Yes | No | No | Yes | 23 |
| F03/T27 | py | E | Yes | No | No | Yes | 23 |
| F03/T27 | rg | B | Yes | No | No | Yes | 14 |
| F04/T45 | ask | A | Yes | Yes | No | Yes | 0 |
| F04/T45 | bt | B | Yes | No | No | Yes | 29 |
| F04/T45 | de | B | Yes | No | Yes | No | 14 |
| F04/T45 | ls | C | Yes | No | No | No | 29 |
| F04/T45 | pf | B | No | No | No | Yes | 39 |
| F04/T45 | pe | A | Yes | No | No | Yes | 23 |
| F04/T45 | py | B | Yes | No | Yes | No | 23 |
| F04/T45 | rg | A | Yes | No | No | No | 14 |
| F04/T49 | ask | A | Yes | Yes | Yes | Yes | 0 |
| F04/T49 | bt | C | Yes | No | No | Yes | 29 |
| F04/T49 | de | B | Yes | No | Yes | No | 14 |
| F04/T49 | ls | B | Yes | No | No | No | 29 |
| F04/T49 | pf | B | No | No | No | Yes | 39 |
| F04/T49 | pe | A | Yes | No | Yes | No | 23 |
| F04/T49 | py | B | Yes | No | No | No | 23 |
| F04/T49 | rg | B | Yes | No | No | No | 14 |
| F04/T50 | ask | A | Yes | Yes | No | Yes | 0 |
| F04/T50 | bt | C | Yes | No | No | No | 23 |
| F04/T50 | de | B | Yes | No | No | No | 14 |
| F04/T50 | ls | C | Yes | No | No | No | 23 |
| F04/T50 | pf | B | No | No | No | No | 31 |
| F04/T50 | pe | B | Yes | No | No | No | 17 |
| F04/T50 | py | B | Yes | No | No | No | 17 |
| F04/T50 | rg | B | Yes | No | No | No | 14 |
| F05/T38 | ask | B | Yes | Yes | Yes | No | 0 |
| F05/T38 | bt | B | No | No | No | No | 24 |
| F05/T38 | de | B | Yes | No | No | No | 14 |
| F05/T38 | ls | B | No | No | No | No | 24 |
| F05/T38 | pf | B | No | No | No | No | 32 |
| F05/T38 | pe | B | Yes | No | No | No | 18 |
| F05/T38 | py | B | Yes | No | No | No | 18 |
| F05/T38 | rg | B | Yes | No | No | No | 14 |
| F07/T29 | ask | A | Yes | Yes | Yes | Yes | 0 |
| F07/T29 | bt | C | Yes | Yes | No | No | 21 |
| F07/T29 | de | B | Yes | Yes | No | No | 14 |
| F07/T29 | ls | B | Yes | Yes | No | No | 21 |
| F07/T29 | pf | B | Yes | Yes | No | No | 29 |
| F07/T29 | pe | B | Yes | Yes | No | No | 15 |
| F07/T29 | py | B | Yes | Yes | No | No | 15 |
| F07/T29 | rg | B | Yes | Yes | No | No | 14 |
| F07/T30 | ask | A | Yes | Yes | Yes | Yes | 0 |
| F07/T30 | bt | B | Yes | Yes | No | No | 21 |
| F07/T30 | de | B | Yes | Yes | No | No | 14 |
| F07/T30 | ls | B | Yes | Yes | No | No | 21 |
| F07/T30 | pf | B | Yes | Yes | No | No | 29 |
| F07/T30 | pe | B | Yes | Yes | No | No | 15 |
| F07/T30 | py | B | Yes | Yes | No | No | 15 |
| F07/T30 | rg | B | Yes | Yes | No | No | 14 |
| F07/T42 | ask | A | Yes | Yes | Yes | Yes | 0 |
| F07/T42 | bt | B | Yes | Yes | No | No | 21 |
| F07/T42 | de | B | Yes | Yes | No | No | 14 |
| F07/T42 | ls | B | Yes | Yes | No | No | 21 |
| F07/T42 | pf | B | Yes | Yes | No | No | 29 |
| F07/T42 | pe | B | Yes | Yes | No | No | 15 |
| F07/T42 | py | B | Yes | Yes | No | No | 15 |
| F07/T42 | rg | B | Yes | Yes | No | No | 14 |
| F07/T43 | ask | A | Yes | Yes | Yes | Yes | 0 |
| F07/T43 | bt | B | Yes | Yes | No | No | 21 |
| F07/T43 | de | B | Yes | Yes | No | No | 14 |
| F07/T43 | ls | B | Yes | Yes | No | No | 21 |
| F07/T43 | pf | B | Yes | Yes | No | No | 29 |
| F07/T43 | pe | B | Yes | Yes | No | No | 15 |
| F07/T43 | py | B | Yes | Yes | No | No | 15 |
| F07/T43 | rg | B | Yes | Yes | No | No | 14 |
| F08/T21 | ask | B | Yes | Yes | No | Yes | 0 |
| F08/T21 | bt | C | Yes | No | No | No | 29 |
| F08/T21 | de | B | Yes | No | No | No | 14 |
| F08/T21 | ls | C | Yes | No | No | No | 29 |
| F08/T21 | pf | C | No | No | No | No | 39 |
| F08/T21 | pe | B | Yes | No | No | No | 23 |
| F08/T21 | py | B | Yes | No | No | No | 23 |
| F08/T21 | rg | B | Yes | No | No | No | 14 |
| F09/T04 | ask | B | Yes | Yes | No | Yes | 0 |
| F09/T04 | bt | C | Yes | No | No | No | 29 |
| F09/T04 | de | B | Yes | No | No | No | 14 |
| F09/T04 | ls | C | Yes | No | No | No | 29 |
| F09/T04 | pf | B | No | No | No | No | 39 |
| F09/T04 | pe | B | Yes | No | No | No | 23 |
| F09/T04 | py | B | Yes | No | No | No | 23 |
| F09/T04 | rg | B | Yes | No | No | No | 14 |
| F09/T19 | ask | A | Yes | Yes | No | Yes | 0 |
| F09/T19 | bt | B | Yes | No | No | No | 29 |
| F09/T19 | de | B | Yes | No | No | No | 14 |
| F09/T19 | ls | C | Yes | No | No | Yes | 29 |
| F09/T19 | pf | B | No | No | No | Yes | 39 |
| F09/T19 | pe | B | Yes | No | No | No | 23 |
| F09/T19 | py | B | Yes | No | No | No | 23 |
| F09/T19 | rg | B | Yes | No | No | No | 14 |
| F10/T29 | ask | A | Yes | Yes | Yes | Yes | 0 |
| F10/T29 | bt | A | Yes | No | Yes | No | 26 |
| F10/T29 | de | A | Yes | No | Yes | No | 14 |
| F10/T29 | ls | A | Yes | No | Yes | Yes | 26 |
| F10/T29 | pf | A | No | No | Yes | Yes | 34 |
| F10/T29 | pe | B | Yes | No | Yes | No | 20 |
| F10/T29 | py | A | Yes | No | Yes | Yes | 20 |
| F10/T29 | rg | A | Yes | No | Yes | Yes | 14 |
| F10/T42 | ask | B | Yes | Yes | No | Yes | 0 |
| F10/T42 | bt | C | Yes | No | No | Yes | 29 |
| F10/T42 | de | B | Yes | No | No | Yes | 14 |
| F10/T42 | ls | C | Yes | No | No | Yes | 29 |
| F10/T42 | pf | B | No | No | No | Yes | 39 |
| F10/T42 | pe | B | Yes | No | No | Yes | 23 |
| F10/T42 | py | B | Yes | No | No | Yes | 23 |
| F10/T42 | rg | B | Yes | No | No | Yes | 14 |
| F10/T43 | ask | C | Yes | Yes | No | Yes | 0 |
| F10/T43 | bt | C | Yes | No | No | Yes | 25 |
| F10/T43 | de | C | Yes | No | No | Yes | 14 |
| F10/T43 | ls | C | Yes | No | No | Yes | 25 |
| F10/T43 | pf | B | No | No | No | Yes | 33 |
| F10/T43 | pe | B | Yes | No | No | Yes | 19 |
| F10/T43 | py | B | Yes | No | No | Yes | 19 |
| F10/T43 | rg | B | Yes | No | No | Yes | 14 |
| F10/T44 | ask | A | Yes | Yes | Yes | Yes | 0 |
| F10/T44 | bt | A | Yes | Yes | No | Yes | 24 |
| F10/T44 | de | B | Yes | No | No | Yes | 14 |
| F10/T44 | ls | A | No | Yes | No | Yes | 24 |
| F10/T44 | pf | B | No | Yes | No | Yes | 32 |
| F10/T44 | pe | A | Yes | No | No | Yes | 18 |
| F10/T44 | py | A | Yes | No | No | Yes | 18 |
| F10/T44 | rg | B | Yes | No | No | Yes | 14 |

## Section C — Qualitative examples

Configure slots in `diagnostic_exemplars.yaml` to render side-by-side snippets here.

## Conclusion (template)

Richer oracles and frameworks that surface trace, state, and matcher witnesses produce more localised failure messages. Output-only or generic assertion shells tend toward lower specificity grades on the same underlying faults.
