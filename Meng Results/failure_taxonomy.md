# Failure taxonomy — incremental discovery layers

Populated from **`tasks/fuzzing/fuzzing_runs.json`** (run `20260531T145454Z`, `framework_trials: 1`, 154 conversations, **62 failures**).

Each layer counts failures **not already explained** by the layers below.

```text
Manual script ──► Simulation (personas) ──► Mutation fuzz
     │                    │                        │
 Manual-known      Simulation-new              Fuzz-new
```

---

## Category definitions

| Category | Meaning |
| -------- | ------- |
| **Manual-known** | Fails on the **manual** arm (canonical scripted conversation). |
| **Simulation-new** | Fails on the **sim** arm and `failure_signature` is **not** among manual failures in this run. |
| **Fuzz-new** | Fails on the **fuzz** arm and `failure_signature` is **not** among manual **or** sim failures in this run. |

**Matching rule:** exact string match on `failure_signature` within this run (`fuzz_new_failures.json` uses the same rule for fuzz).

---

## Summary table

| Category | Meaning | Failing conversations | Distinct signatures | Tasks |
| -------- | ------- | --------------------: | ------------------: | ----- |
| **Manual-known** | Manual script already fails | **3** | **3** | T29, T38, T43 |
| **Simulation-new** | Sim finds something manual did not | **34** | **24** | T03, T04, T20, T29, T38, T42, T43, T45 |
| **Fuzz-new** | Fuzz finds something manual and sim did not | **25** | **18** | T03, T04, T17, T20, T29, T30, T35, T38, T42, T45 |

**Per arm:**

| Arm | Failures | Manual-known | Simulation-new | Fuzz-new |
| --- | -------: | -----------: | -------------: | -------: |
| manual | 3 | 3 | — | — |
| sim | 34 | — | 34 | — |
| fuzz | 25 | — | — | 25 |

3 + 34 + 25 = **62**.

---

## Is the study already doing this?

| Layer | In the pipeline? |
| ----- | ---------------- |
| **Manual-known** | Yes — manual arm pass/fail per task. |
| **Simulation-new** | Yes — sim failures whose signature ∉ manual (derived from `fuzzing_runs.json`; no separate JSON file). |
| **Fuzz-new** | Yes — `fuzz_new_failures.json` (fuzz signatures ∉ manual ∪ sim). |

In this run, **no** signature appears in both manual and sim (`manual ∩ sim = ∅`), so all **34** sim failures count as Simulation-new.

---

## Examples

### Manual-known (3)

| Task | Issue (abridged) |
| ---- | ---------------- |
| T29 | `assert_tool_calls` — wrong line / replacement SIM path |
| T38 | `assert_tool_calls` — specialist workflow ordering |
| T43 | `assert_output` — ticket / corrected-line binding |

### Simulation-new (34)

Personas hit failures the script does not — e.g. T42 opens a ticket when the user refused a replacement SIM; T45 pre-auth disclosure; T03 personas trigger ticket-in-output failures while **manual passes**.

### Fuzz-new (25)

Listed in **`fuzz_new_failures.json`**. All fuzz failures use signatures not seen on manual or sim arms (including T03 under `ambiguous_acknowledgement`). Same task can fail on manual with one signature and on fuzz with another (T29, T38, T43).

---

## Per-task matrix

| Task | Manual | Sim new | Fuzz new |
| ---- | :----: | :-----: | :------: |
| T03 | Pass | ✓ | ✓ |
| T04 | Pass | ✓ | ✓ |
| T17 | Pass | | ✓ |
| T20 | Pass | ✓ | ✓ |
| T27 | Pass | | |
| T29 | Fail | ✓ | ✓ |
| T30 | Pass | | ✓ |
| T35 | Pass | | ✓ |
| T38 | Fail | ✓ | ✓ |
| T42 | Pass | ✓ | ✓ |
| T43 | Fail | ✓ | |
| T44 | Pass | | |
| T45 | Pass | ✓ | ✓ |
| T49 | Pass | | |

---

*Sources: `fuzzing_runs.json`, `fuzz_new_failures.json`.*
