# User-simulation shrink study results

Generated: 2026-05-31T16:25:13.751254+00:00

## Candidate / stability

| Metric | Value |
|--------|------:|
| Simulated conversations | 60 |
| Failing conversations | 35 |
| Stable failures | 12 |
| Flaky | 10 |
| Non-reproducing | 8 |
| Capture failed | 5 |
| Selected for shrink (cap 15) | 15 |
| Max verification attempts per shrink | 10 |

## Shrink per failure

| Failure | Task | Persona | Orig turns | Shrunk turns | Turn reduction | Orig tokens | Shrunk tokens | Verif attempts | Same sig | Time (s) |
|---------|------|---------|------------:|-------------:|---------------:|------------:|--------------:|----------------:|---------:|---------:|
| SIM-T20-0 | T20 | seed0 | 1 | 1 | 0.0% | 27 | 26 | 10 | Yes | 1158.42 |
| SIM-T38-2 | T38 | seed2 | 1 | 1 | 0.0% | 28 | 28 | 3 | Yes | 755.95 |
| SIM-T38-4 | T38 | seed4 | 1 | 1 | 0.0% | 20 | 20 | 3 | Yes | 628.94 |
| SIM-T42-1 | T42 | seed1 | 0 | 0 | 0.0% | 0 | 0 | 0 | Yes | 121.84 |
| SIM-T20-2 | T20 | seed2 | 2 | 1 | 50.0% | 50 | 24 | 10 | Yes | 753.34 |
| SIM-T20-1 | T20 | seed1 | 2 | 1 | 50.0% | 57 | 26 | 10 | Yes | 1399.48 |
| SIM-T43-0 | T43 | seed0 | 0 | 0 | 0.0% | 0 | 0 | 0 | Yes | 204.36 |
| SIM-T29-0 | T29 | seed0 | 1 | 1 | 0.0% | 27 | 27 | 10 | Yes | 291.93 |
| SIM-T29-1 | T29 | seed1 | 1 | 1 | 0.0% | 30 | 29 | 10 | Yes | 313.47 |
| SIM-T29-2 | T29 | seed2 | 1 | 1 | 0.0% | 41 | 41 | 8 | Yes | 294.1 |
| SIM-T43-4 | T43 | seed4 | 0 | 0 | 0.0% | 0 | 0 | 0 | Yes | 147.05 |
| SIM-T45-0 | T45 | seed0 | 1 | 1 | 0.0% | 39 | 38 | 10 | Yes | 1287.82 |

## All shrink attempts (selected pool)

| Failure | Task | Persona | Status | Orig turns | Shrunk turns | Verif attempts | Same sig |
|---------|------|---------|--------|------------:|-------------:|----------------:|---------:|
| SIM-T20-0 | T20 | seed0 | ok | 1 | 1 | 10 | Yes |
| SIM-T38-2 | T38 | seed2 | ok | 1 | 1 | 3 | Yes |
| SIM-T38-0 | T38 | seed0 | failed_verify | 1 | 1 | 3 | No |
| SIM-T42-0 | T42 | seed0 | failed_verify | 0 | 0 | 0 | No |
| SIM-T38-4 | T38 | seed4 | ok | 1 | 1 | 3 | Yes |
| SIM-T42-1 | T42 | seed1 | ok | 0 | 0 | 0 | Yes |
| SIM-T20-2 | T20 | seed2 | ok | 2 | 1 | 10 | Yes |
| SIM-T20-1 | T20 | seed1 | ok | 2 | 1 | 10 | Yes |
| SIM-T43-0 | T43 | seed0 | ok | 0 | 0 | 0 | Yes |
| SIM-T29-0 | T29 | seed0 | ok | 1 | 1 | 10 | Yes |
| SIM-T29-1 | T29 | seed1 | ok | 1 | 1 | 10 | Yes |
| SIM-T29-2 | T29 | seed2 | ok | 1 | 1 | 8 | Yes |
| SIM-T43-4 | T43 | seed4 | ok | 0 | 0 | 0 | Yes |
| SIM-T45-0 | T45 | seed0 | ok | 1 | 1 | 10 | Yes |
| SIM-T45-1 | T45 | seed1 | failed_verify | 1 | 1 | 8 | No |

## Shrink aggregates

| Metric | Value |
|--------|------:|
| Stable failures attempted | 15 |
| Successfully shrunk | 12 |
| Failed to shrink | 3 |
| Median turn reduction | 0.0% |
| Median token reduction | 0.0% |
| Median shrink time (s) | 471.21 |
| Median verification attempts | 9.00 |
| Same-signature preservation rate | 100.0% |

