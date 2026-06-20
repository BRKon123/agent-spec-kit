# Diagnostic quality comparison (telecom fault detection)

Six frameworks report the same underlying full-scenario failure with different error formatting:

`agent_spec_kit`, `pytest_plain`, `langsmith`, `pydantic_evals`, `promptfoo`, `braintrust`

- **agent_spec_kit:** Rich failure panel from `fault_detection_primary.log` (live run).
- **Baselines:** programmatic checks on exported artifacts (trace JSONL, store snapshot, output text) — see [`FRAMEWORK_RESEARCH.md`](FRAMEWORK_RESEARCH.md).

## Commands

```bash
cd benchmarks/telecom_support

# 1) Live fault run (writes log + trace JSONL + store snapshots)
uv run python scripts/run_fault_detection.py --run

# 2) Bundle per-slot artifacts
uv run python scripts/export_diagnostic_artifacts.py

# 3) Run native framework checks → failure_messages.yaml
uv run python scripts/collect_diagnostic_failures.py

# 4) LLM specificity scoring + table
OPENAI_API_KEY=... uv run python scripts/extract_diagnostic_quality.py --refresh-llm
uv run python scripts/generate_diagnostic_quality_table.py
```

Regenerate fault scenarios with trace binding (after bootstrap change):

```bash
uv run python scripts/bootstrap_fault_detection.py
```
