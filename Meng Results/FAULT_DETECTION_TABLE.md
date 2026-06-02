# Fault detection table (F01–F10)

Generated from real fault-detection run data. Regenerate:

```bash
uv run python benchmarks/telecom_support/scripts/generate_fault_detection_table.py
```

- Generated: 2026-05-26T15:48:25.168112+00:00
- Fault log: `tasks/fault_detection/fault_detection_primary.log`
- Matrix hash: `b6c509c52ff5ad54`
- Run exit code: `1`
- Parsed scenarios: `152` / `152`
- Baseline (frozen): `tasks/calibration_logs/baseline_report.md`

## Summary (detection rate = detected / eligible)

| Fault | O | S | T | F |
|-------|---|---|---|---|
| F01 | 0/4 (0%) | 0/2 (0%) | — | 1/2 (50%) |
| F02 | 0/3 (0%) | 3/3 (100%) | 2/3 (67%) | 3/3 (100%) |
| F03 | 0/4 (0%) | 3/3 (100%) | 0/3 (0%) | 2/2 (100%) |
| F04 | 1/4 (25%) | 3/4 (75%) | 0/4 (0%) | 3/4 (75%) |
| F05 | 0/3 (0%) | 0/3 (0%) | 2/2 (100%) | 1/1 (100%) |
| F06 | 3/4 (75%) | 2/4 (50%) | — | — |
| F07 | 2/4 (50%) | 2/4 (50%) | 4/4 (100%) | 4/4 (100%) |
| F08 | 0/4 (0%) | 0/1 (0%) | 3/4 (75%) | 1/2 (50%) |
| F09 | 2/4 (50%) | 2/4 (50%) | 2/4 (50%) | 2/4 (50%) |
| F10 | 1/4 (25%) | 0/4 (0%) | 1/3 (33%) | 4/4 (100%) |

## Detail grid (primary matrix)

Legend: **detected** = eligible and fault scenario failed; **missed** = eligible but passed; **N/A** = reference failed baseline; **incomplete** = no run line.

| Fault | Task | O | S | T | F |
|-------|------|---|---|---|---|
| F01 | T03 | missed | missed | N/A | missed |
| F01 | T37 | missed | N/A | N/A | N/A |
| F01 | T44 | missed | missed | N/A | detected |
| F01 | T48 | missed | N/A | N/A | N/A |
| F02 | T29 | missed | detected | detected | detected |
| F02 | T43 | missed | detected | missed | detected |
| F02 | T46 | missed | detected | detected | detected |
| F03 | T14 | missed | detected | missed | N/A |
| F03 | T17 | missed | detected | missed | detected |
| F03 | T22 | missed | N/A | N/A | N/A |
| F03 | T27 | missed | detected | missed | detected |
| F04 | T20 | missed | missed | missed | missed |
| F04 | T45 | missed | detected | missed | detected |
| F04 | T49 | missed | detected | missed | detected |
| F04 | T50 | detected | detected | missed | detected |
| F05 | T05 | missed | missed | detected | N/A |
| F05 | T38 | missed | missed | detected | detected |
| F05 | T40 | missed | missed | N/A | N/A |
| F06 | T09 | missed | missed | N/A | N/A |
| F06 | T10 | detected | missed | N/A | N/A |
| F06 | T23 | detected | detected | N/A | N/A |
| F06 | T33 | detected | detected | N/A | N/A |
| F07 | T29 | missed | missed | detected | detected |
| F07 | T30 | detected | missed | detected | detected |
| F07 | T42 | detected | detected | detected | detected |
| F07 | T43 | missed | detected | detected | detected |
| F08 | T18 | missed | N/A | detected | N/A |
| F08 | T21 | missed | N/A | detected | detected |
| F08 | T26 | missed | N/A | detected | N/A |
| F08 | T35 | missed | missed | missed | missed |
| F09 | T04 | detected | detected | detected | detected |
| F09 | T19 | detected | detected | detected | detected |
| F09 | T35 | missed | missed | missed | missed |
| F09 | T34 | missed | missed | missed | missed |
| F10 | T29 | missed | missed | detected | detected |
| F10 | T42 | missed | missed | missed | detected |
| F10 | T43 | detected | missed | missed | detected |
| F10 | T44 | missed | missed | N/A | detected |

## Notes

- Denominator uses only task×oracle slots where the **frozen unsteered reference** passed (`eligibility.json` from `baseline_T01_T50.log`).
- Reference agent and baseline artifacts are not re-run or modified by this pipeline.
- Sparse columns (e.g. F01/T on T03, T44) reflect baseline gaps, not missing fault injection.
