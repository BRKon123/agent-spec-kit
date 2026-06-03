# User-simulation shrink study results

Generated: 2026-06-03T12:03:46.533962+00:00

## Candidate / stability

| Metric | Value |
|--------|------:|
| Simulated conversations | 60 |
| Failing conversations | 29 |
| Stable failures | 15 |
| Flaky | 9 |
| Non-reproducing | 1 |
| Capture failed | 4 |
| Selected for shrink (cap 15) | 15 |
| Max verification attempts per shrink | 10 |

## Shrink per failure

| Failure | Task | Persona | Orig turns | Shrunk turns | Turn reduction | Orig tokens | Shrunk tokens | Verif attempts | Same sig | Time (s) |
|---------|------|---------|------------:|-------------:|---------------:|------------:|--------------:|----------------:|---------:|---------:|
| SIM-T29-1 | T29 | seed1 | 1 | 1 | 0.0% | 20 | 20 | 10 | Yes | 341.66 |
| SIM-T29-0 | T29 | seed0 | 1 | 1 | 0.0% | 32 | 32 | 10 | Yes | 461.76 |
| SIM-T29-2 | T29 | seed2 | 1 | 1 | 0.0% | 43 | 43 | 10 | Yes | 457.98 |
| SIM-T29-3 | T29 | seed3 | 1 | 1 | 0.0% | 24 | 24 | 10 | Yes | 339.32 |
| SIM-T29-4 | T29 | seed4 | 1 | 1 | 0.0% | 27 | 27 | 10 | Yes | 377.61 |
| SIM-T43-3 | T43 | seed3 | 1 | 1 | 0.0% | 32 | 32 | 10 | Yes | 2609.49 |
| SIM-T38-3 | T38 | seed3 | 1 | 1 | 0.0% | 31 | 31 | 3 | Yes | 709.97 |
| SIM-T20-0 | T20 | seed0 | 1 | 1 | 0.0% | 27 | 26 | 10 | Yes | 1324.63 |
| SIM-T20-2 | T20 | seed2 | 2 | 1 | 50.0% | 48 | 24 | 10 | Yes | 911.4 |
| SIM-T20-1 | T20 | seed1 | 2 | 1 | 50.0% | 47 | 21 | 10 | Yes | 1139.09 |
| SIM-T20-4 | T20 | seed4 | 1 | 1 | 0.0% | 28 | 28 | 10 | Yes | 726.14 |
| SIM-T20-3 | T20 | seed3 | 2 | 1 | 50.0% | 58 | 24 | 10 | Yes | 872.65 |

## All shrink attempts (selected pool)

| Failure | Task | Persona | Status | Orig turns | Shrunk turns | Verif attempts | Same sig |
|---------|------|---------|--------|------------:|-------------:|----------------:|---------:|
| SIM-T29-1 | T29 | seed1 | ok | 1 | 1 | 10 | Yes |
| SIM-T29-0 | T29 | seed0 | ok | 1 | 1 | 10 | Yes |
| SIM-T29-2 | T29 | seed2 | ok | 1 | 1 | 10 | Yes |
| SIM-T29-3 | T29 | seed3 | ok | 1 | 1 | 10 | Yes |
| SIM-T29-4 | T29 | seed4 | ok | 1 | 1 | 10 | Yes |
| SIM-T43-3 | T43 | seed3 | ok | 1 | 1 | 10 | Yes |
| SIM-T45-2 | T45 | seed2 | failed_verify | 2 | 1 | 10 | No |
| SIM-T04-2 | T04 | seed2 | failed_verify | 1 | 1 | 5 | No |
| SIM-T04-4 | T04 | seed4 | failed_verify | 1 | 1 | 8 | No |
| SIM-T38-3 | T38 | seed3 | ok | 1 | 1 | 3 | Yes |
| SIM-T20-0 | T20 | seed0 | ok | 1 | 1 | 10 | Yes |
| SIM-T20-2 | T20 | seed2 | ok | 2 | 1 | 10 | Yes |
| SIM-T20-1 | T20 | seed1 | ok | 2 | 1 | 10 | Yes |
| SIM-T20-4 | T20 | seed4 | ok | 1 | 1 | 10 | Yes |
| SIM-T20-3 | T20 | seed3 | ok | 2 | 1 | 10 | Yes |

## Shrink aggregates

| Metric | Value |
|--------|------:|
| Stable failures attempted | 15 |
| Successfully shrunk | 12 |
| Failed to shrink | 3 |
| Median turn reduction | 0.0% |
| Median token reduction | 0.0% |
| Median shrink time (s) | 718.06 |
| Median verification attempts | 10.00 |
| Same-signature preservation rate | 100.0% |

