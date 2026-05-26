# Fault detection (F01–F10)

Mutation-style fault families run against the **same task oracles** as reference scenarios, with detection rates computed only on slots where the **frozen unsteered baseline** passed (`eligibility.json`).

## Files

| File | Role |
|------|------|
| `fault_matrix.yaml` | Primary (22) and expansion task×fault pairs |
| `eligibility.json` | Baseline pass flags (from `baseline_T01_T50.log`, do not refresh unless baseline is replaced) |
| `generated/` | Bootstrap scenarios (`bootstrap_fault_detection.py`) |
| `fault_detection_results.json` | Parsed from live fault run log |
| `FAULT_DETECTION_TABLE.md` | Generated summary + detail grid |
| `FAULT_DIAGNOSTICS.md` | Generated exemplar diagnostics |

## Commands

```bash
# Regenerate scenarios after editing tasks/manual/test_Txx.py
uv run python benchmarks/telecom_support/scripts/bootstrap_fault_detection.py

# Run matrix (~88 scenarios; requires OPENAI_API_KEY)
TELCO_DISABLE_CALIBRATION_STEERING=1 OPENAI_API_KEY=... \
  uv run python benchmarks/telecom_support/scripts/run_fault_detection.py --run --workers 4

# Regenerate tables from results JSON
uv run python benchmarks/telecom_support/scripts/generate_fault_detection_table.py
```

Scenarios are discovered only under `generated/` to avoid duplicate fixtures with `tasks/manual/`.
