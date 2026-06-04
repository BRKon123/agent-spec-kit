# Native port policy (expressiveness benchmark)

Each framework port must express checks with **that library’s own evaluation tools**. The benchmark compares *how authors write tests* in each ecosystem—not whether every port shares the same imperative Python.

## Shared mental model (agent evals)

| Level | What we check | Example checks |
| --- | --- | --- |
| Final response | Output text / format / policy phrases | C01 |
| Trajectory / tools | Tool presence, args, order, forbidden tools | C05–C07, C09–C10, C12 (partial) |
| Environment / state | DB or ticket store postconditions | C11, C12 (partial) |

[`shared/canonical_checks.py`](shared/canonical_checks.py) encodes the semantic oracle for golden-trace parity only.

## Rules

1. **`# CHECK_START` / `# CHECK_END`** — check logic in the target framework’s idioms only. Keep one CHECK region per specimen (C01–C12) even when checks live in a single native file.
2. **Harness glue** (load trace, adapters, `run_evaluator`) stays **outside** CHECK regions.
3. **`scripts/materialize_inline_checks.py`** regenerates **pytest** only; other ports are hand-maintained.
4. Use **`shared/trace_helpers.py`** only when no native primitive applies to frozen JSON traces (document in port comments).
5. **Native file shape** — do not split ports into twelve artificial top-level modules if the framework normally uses one artifact:
   - **Pydantic Evals:** `dataset.py` — `Dataset` + `Case` per specimen (`EXPRESSIVENESS_DATASET`).
   - **LangSmith:** `experiment.py` — code evaluators + `EXPERIMENT_EVALUATORS` list.
   - **Braintrust:** `experiment.py` — `Score` scorers + `EXPRESSIVENESS_SCORERS` list.
   - **Promptfoo:** one `promptfooconfig.yaml` (+ small `assert_c11.py` / `assert_c12.py` where YAML cannot express store oracles).
   - **pytest / agent_spec_kit:** separate tests or scenarios per check is natural — keep that layout.
6. **LOC and readability** — `shared/check_snippets.py` still extracts **per-check** snippets from CHECK regions (optional `# check: Cxx` tag before each block). Tables and thesis summaries that report a single number per framework should use the **mean across the twelve checks** (same as averaging per-check LOC or clarity grades), not the raw sum of one shared file.

## Framework idioms (what each port should use)

| Framework | Native surface in this repo |
| --- | --- |
| agent_spec_kit | `scenario`, `assert_output`, `assert_tool_calls`, `forbid_tool_calls`, `m.*` matchers |
| pytest | Plain **`assert`** + small trace helpers (`walk_root_tools`, `ordered_subsequence`) — intentional imperative baseline |
| LangSmith | Code evaluators returning `{"key","score"}`; **`agentevals`** `create_trajectory_match_evaluator`; **`jsonschema`** for structured tool results |
| Pydantic Evals | **`Contains`**, **`IsInstance`**, **`HasMatchingSpan`** + **`SpanQuery`** on harness-built **`SpanTree`**; custom **`Evaluator`** + **`metadata["tool_calls"]`**; **`BaseModel`** validation |
| Braintrust | **`Score`** scorers; **`metadata["tool_calls"]`** (hooks pattern); **`jsonschema`** for structured results |
| Promptfoo | YAML **`icontains-*`**, **`is-json`**, **`trajectory:tool-*`**, **`javascript`**; **`python`** only for store oracles (C11, C12 state) |
| agent_spec_kit | Scenario DSL + **`m.*`** matchers (reference port — already native) |

## LangSmith / agentevals notes

- Trajectory checks use [`agentevals.trajectory.match`](https://pypi.org/project/agentevals/) (installed in the `expressiveness` dependency group).
- Frozen traces are adapted to OpenAI-style message lists in `implementations/langsmith/trajectory_bridge.py` (harness only).
- **C05** (ordered subsequence with extras): `superset` + `tool_args_match_mode="ignore"` plus a short order walk (agentevals has no single mode for this).
- **C10** (unordered with extras): `superset` + `ignore` on required tools, not `unordered` (which requires the exact tool set).
- **C07**: `strict` trajectory + `tool_args_match_overrides` for `line_id`.
- Structured tool JSON (C02, C04, C08): **`jsonschema.validate`** in code evaluators—not Pydantic models in LangSmith ports.

## Braintrust notes

- Scorers follow `(input, output, expected, metadata=...)` and read **`metadata["tool_calls"]`** as in Braintrust agent eval docs (task logs intermediate behaviour for scorers).
- Harness builds metadata via `metadata_for_trace()` in `test_scorers.py`.

## Pydantic Evals notes

- Harness builds **`SpanTree`** in `implementations/pydantic_evals/span_tree_bridge.py` (frozen trace → OTel-style spans).
- **C06:** `HasMatchingSpan` + `not any(forbidden span)`.
- **C10:** `HasMatchingSpan` with `and_` + `some_descendant_has` for required tools.
- **C05/C07/C12:** custom `@dataclass` **`Evaluator`** reading **`ctx.metadata["tool_calls"]`** (documented custom-evaluator pattern).
- **C02/C03:** **`IsInstance(type_name="dict")`** then **`BaseModel.model_validate`**.

## Pytest notes

- Stays **imperative `assert`** on trace dicts — typical plain-pytest agent tests without a DSL.
- Not synced from `materialize_inline_checks.py` (all ports are hand-maintained).

## Promptfoo notes

- Provider emits `trace.spans` for **`trajectory:*`** asserts (`trace_spans.py`).
- **C12:** `trajectory:tool-sequence` in YAML + **`python`** for store oracle only.
- **C11:** **`python`** only (no DB assert type).
- **C03/C09:** **`javascript`** (conditional / nested children — no matching YAML primitive).

## agent_spec_kit notes

- Already uses matchers (`m.object`, `forbid_tool_calls`, `assert_tool_calls`); no change required for native policy.

## Parity

All ports must pass golden traces (`tests/test_canonical_uniformity.py`). Source shape may differ; policy is in [`CANONICAL_SPEC.md`](CANONICAL_SPEC.md).
