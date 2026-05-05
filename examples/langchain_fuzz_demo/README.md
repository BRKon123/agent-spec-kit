# LangChain fuzz / shrink / extract demo

Live example (requires `OPENAI_API_KEY`) showing:

- `fuzz_conversation` with a `behaviour_grammar` strategy (`ek.fuzz`)
- `ShrinkConfig` + `ExtractionConfig` on `@ek.scenario` (activated by CLI flags)
- A non-fuzz baseline scenario (useful when comparing experiments: fuzzed rows are excluded from the compare grid but listed under **excluded fuzz scenarios** in the API)

## Run

From the repo root:

```bash
OPENAI_API_KEY=... uv run agent-spec-kit run examples/langchain_fuzz_demo/
```

Expect **one failing scenario** (`test_multiply_fuzz_strict_assert`): it is meant to fail
without `--shrink` because the strict tool matcher disagrees with the last agent turn
after mostly off-topic fuzz lines. The baseline and lenient fuzz scenarios should pass.

## Shrink (per-trial isolation)

```bash
OPENAI_API_KEY=... uv run agent-spec-kit run examples/langchain_fuzz_demo/ --shrink
```

## Shrink + extract regression source

Writes `regressions/extracted.py` next to this README (gitignored):

```bash
OPENAI_API_KEY=... uv run agent-spec-kit run examples/langchain_fuzz_demo/ --shrink --extract
```

List extractions recorded for a run:

```bash
uv run agent-spec-kit regressions <run_id>
```

## UI

- `uv run agent-spec-kit ui` — open a run: **fuzz trials** table, trace drawer **phase errors** (if any), and **fuzz trials** summary on repeat trace.
- Compare two experiments that include fuzzed runs: the UI shows a **fuzz scenarios excluded** banner when the API returns `excluded_fuzz_scenarios`.
