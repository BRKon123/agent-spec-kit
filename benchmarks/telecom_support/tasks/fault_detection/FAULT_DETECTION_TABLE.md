# Fault detection table (F01–F10)

Generated from real fault-detection run data. Regenerate:

```bash
uv run python benchmarks/telecom_support/scripts/generate_fault_detection_table.py
```

- Generated: 2026-05-26T15:27:25.338274+00:00
- Fault log: `tasks/fault_detection/fault_detection_primary.log`
- Matrix hash: `5fdf0e3ecb79e0d1`
- Run exit code: `1`
- Parsed scenarios: `64` / `152`
- Baseline (frozen): `tasks/calibration_logs/baseline_report.md`

## Summary (detection rate = detected / eligible)

| Fault | O | S | T | F |
|-------|---|---|---|---|
| F01 | 0/4 (0%) | 0/2 (0%) | — | 0/2 (0%) |
| F02 | 0/3 (0%) | 0/3 (0%) | 0/3 (0%) | 0/3 (0%) |
| F03 | 0/4 (0%) | 0/3 (0%) | 0/3 (0%) | 0/2 (0%) |
| F04 | 0/4 (0%) | 0/4 (0%) | 0/4 (0%) | 0/4 (0%) |
| F05 | 0/3 (0%) | 0/3 (0%) | 0/2 (0%) | 0/1 (0%) |
| F06 | 0/4 (0%) | 0/4 (0%) | — | — |
| F07 | 2/4 (50%) | 2/4 (50%) | 4/4 (100%) | 4/4 (100%) |
| F08 | 0/4 (0%) | 0/1 (0%) | 3/4 (75%) | 1/2 (50%) |
| F09 | 2/4 (50%) | 2/4 (50%) | 2/4 (50%) | 2/4 (50%) |
| F10 | 0/4 (0%) | 2/4 (50%) | 1/3 (33%) | 3/4 (75%) |

## Detail grid (primary matrix)

Legend: **detected** = eligible and fault scenario failed; **missed** = eligible but passed; **N/A** = reference failed baseline; **incomplete** = no run line.

| Fault | Task | O | S | T | F |
|-------|------|---|---|---|---|
| F01 | T03 | incomplete | incomplete | N/A | incomplete |
| F01 | T37 | incomplete | N/A | N/A | N/A |
| F01 | T44 | incomplete | incomplete | N/A | incomplete |
| F01 | T48 | incomplete | N/A | N/A | N/A |
| F02 | T29 | incomplete | incomplete | incomplete | incomplete |
| F02 | T43 | incomplete | incomplete | incomplete | incomplete |
| F02 | T46 | incomplete | incomplete | incomplete | incomplete |
| F03 | T14 | incomplete | incomplete | incomplete | N/A |
| F03 | T17 | incomplete | incomplete | incomplete | incomplete |
| F03 | T22 | incomplete | N/A | N/A | N/A |
| F03 | T27 | incomplete | incomplete | incomplete | incomplete |
| F04 | T20 | incomplete | incomplete | incomplete | incomplete |
| F04 | T45 | incomplete | incomplete | incomplete | incomplete |
| F04 | T49 | incomplete | incomplete | incomplete | incomplete |
| F04 | T50 | incomplete | incomplete | incomplete | incomplete |
| F05 | T05 | incomplete | incomplete | incomplete | N/A |
| F05 | T38 | incomplete | incomplete | incomplete | incomplete |
| F05 | T40 | incomplete | incomplete | N/A | N/A |
| F06 | T09 | incomplete | incomplete | N/A | N/A |
| F06 | T10 | incomplete | incomplete | N/A | N/A |
| F06 | T23 | incomplete | incomplete | N/A | N/A |
| F06 | T33 | incomplete | incomplete | N/A | N/A |
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
| F10 | T42 | missed | missed | missed | missed |
| F10 | T43 | missed | detected | missed | detected |
| F10 | T44 | missed | detected | N/A | detected |

## Notes

- Denominator uses only task×oracle slots where the **frozen unsteered reference** passed (`eligibility.json` from `baseline_T01_T50.log`).
- Reference agent and baseline artifacts are not re-run or modified by this pipeline.
- Sparse columns (e.g. F01/T on T03, T44) reflect baseline gaps, not missing fault injection.
