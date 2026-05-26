# Diagnostic quality comparison (telecom fault detection)

Six frameworks report the same underlying full-scenario failure with different error formatting:

`agent_spec_kit`, `pytest_plain`, `langsmith`, `pydantic_evals`, `promptfoo`, `braintrust`

- **agent_spec_kit** uses the Rich failure panel from `fault_detection_primary.log`.
- Baselines use characteristic message shapes derived from the parsed panel (`shared/run_framework.py`).

## Commands

```bash
cd benchmarks/telecom_support

uv run python scripts/collect_diagnostic_failures.py

OPENAI_API_KEY=... uv run python scripts/extract_diagnostic_quality.py

uv run python scripts/generate_diagnostic_quality_table.py
```

Requires a completed fault-detection log with Rich `╭ FAIL ... ╯` panels.
