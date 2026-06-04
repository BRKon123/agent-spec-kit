# Expressiveness / authoring-effort comparison harness

Twelve check-type specimens (`C01`–`C12`) implemented in parallel across:

| Framework | Path |
| --- | --- |
| agent_spec_kit | `implementations/agent_spec_kit/test_checks.py` |
| Plain pytest | `implementations/pytest_plain/test_canonical_checks.py` |
| LangSmith | `implementations/langsmith/experiment.py` (code evaluators + `agentevals` trajectories + `jsonschema`; `evaluators.py` re-exports) |
| Pydantic Evals-style | `implementations/pydantic_evals/dataset.py` (`Dataset` / `Case`; `evaluators.py` re-exports) |
| Promptfoo | `implementations/promptfoo/promptfooconfig.yaml` |
| Braintrust | `implementations/braintrust/experiment.py` (`Score` scorers; `scorers.py` re-exports) |

Frozen traces live in `traces/` for deterministic checks (no API key in CI).

**Oracle parity:** Every framework enforces the same policy using **native** authoring tools in `# CHECK_START`/`# CHECK_END` (see [`NATIVE_PORT_POLICY.md`](NATIVE_PORT_POLICY.md), [`CANONICAL_SPEC.md`](CANONICAL_SPEC.md)). [`shared/canonical_checks.py`](shared/canonical_checks.py) is the semantic reference for golden traces; `uv run python scripts/materialize_inline_checks.py` regenerates **pytest** ports only.

## Run agent_spec_kit (scripted traces)

```bash
uv run agent-spec-kit run benchmarks/expressiveness/ --tags expressiveness
```

Skips `C01` LLM rubric unless `OPENAI_API_KEY` is set (or run with `--tags C02` etc.).

## Run plain pytest

```bash
cd benchmarks/expressiveness && uv run pytest tests/ implementations/langsmith/ implementations/pydantic_evals/ implementations/braintrust/ implementations/pytest_plain/ -q
```

## Record live traces (optional)

```bash
OPENAI_API_KEY=... uv run python benchmarks/expressiveness/scripts/record_traces.py --check C05
```

## Regenerate comparison table

```bash
uv run python benchmarks/expressiveness/scripts/generate_table.py
```

Output: [EXPRESSIVENESS_TABLE.md](EXPRESSIVENESS_TABLE.md) — includes **LOC** (`ask/py/ls/pe/pf/bt`) and **failure specificity** (`A`–`E`) rubrics below the main table.

LOC uses `# CHECK_START` / `# CHECK_END` in each port file.

**Failure samples:** Intentional fail traces live in `traces_fail/`. Capture real messages and refresh grades:

```bash
uv run python scripts/collect_failure_samples.py
uv run python scripts/generate_table.py
```

See [`FAILURE_SAMPLES.md`](FAILURE_SAMPLES.md) and [`failures_samples.yaml`](failures_samples.yaml).

## Authoring clarity (LLM-judged, A–D)

Same 72 cells as LOC (12 checks × 6 frameworks): non-comment lines between `CHECK_START`/`CHECK_END`. One combined letter grade per cell (**A best, D worst**): test intent, scenario message/check flow, and how easy the code is to understand. Distinct from failure-message specificity (**A**–**E** on diagnostic messages).

```bash
cd benchmarks/expressiveness
uv run python scripts/score_readability_quality.py
uv run python scripts/generate_readability_table.py
```

Requires `OPENAI_API_KEY`. Default judge: `openai:gpt-5-mini` (strict intent-based rubric `clarity-v6`). Output: [`READABILITY_TABLE.md`](READABILITY_TABLE.md), records in `readability_records.json`. Use `--force-rescore` to refresh cached cells after snippet changes.

## Library API: `forbid_tool_calls`

```python
s.forbid_tool_calls([m.tool_call("apply_bill_credit")], ordered=True, allow_extras=True)
```

Distinct from `assert_tool_calls([], allow_extras=False)` (no tools at all).
