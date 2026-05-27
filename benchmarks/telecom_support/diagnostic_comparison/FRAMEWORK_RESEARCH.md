# Framework research — telecom diagnostic comparison

How each baseline library reports evaluation failures, and how this benchmark runs checks **offline** on captured agent_spec_kit artifacts (no second live agent run).

## Benchmark constraint

- **Agent execution:** `agent-spec-kit run` on [`tasks/fault_detection/generated/`](../tasks/fault_detection/generated/) only.
- **Baselines:** programmatic evaluators/assertions over exported JSON artifacts (trace turns, final output, store snapshot).
- **Not in scope:** hosted `evaluate()` / `promptfoo eval` / Braintrust `Eval()` against a live LLM for each slot (optional future work).

## pytest / pytest_plain

**Docs:** [pytest assertion introspection](https://docs.pytest.org/en/stable/how-to/assert.html)

**Failure shape:** `AssertionError` with message from `assert` (e.g. `expected zero credits, found 2`).

**Our port:** plain Python functions in `implementations/pytest_plain/` that load an artifact, rebuild `TelcoStore`, run the same oracle/matcher logic as the scenario, and let `AssertionError` propagate. Captured as `str(exc)`.

## LangSmith

**Docs:** [Code evaluator SDK](https://docs.langchain.com/langsmith/code-evaluator-sdk), [`EvaluationResult`](https://github.com/langchain-ai/langsmith-sdk/blob/main/python/langsmith/evaluation/evaluator.py)

**Failure shape (programmatic):** `{"key": "<metric>", "score": 0}` or `EvaluationResult(key=..., score=0, comment="...")`.

**Our port:** evaluator functions `(outputs: dict) -> dict` mirroring expressiveness; on fail return `str({"key": ..., "score": 0})`. Optional `comment` when check logic provides a reason.

**Full `evaluate()`:** would log runs to LangSmith cloud; failure text in UI differs. We document but do not require API keys for this study.

## Pydantic Evals

**Docs:** [Pydantic Evals](https://pydantic.dev/docs/ai/evals/evals/), [`EvaluatorFailure`](https://pydantic.dev/docs/ai/api/pydantic_evals/evaluators/)

**Failure shape:** `EvaluatorFailure(name, error_message, error_stacktrace)` or raised `AssertionError` inside custom `Evaluator.evaluate()`.

**Our port:** same inlined check bodies as pytest; wrap failures as `AssertionError` or a small dataclass serialized to string. Optional later: wire `pydantic_evals.Dataset` if we add `pydantic-evals` dependency.

## Promptfoo

**Docs:** [Python assertions](https://www.promptfoo.dev/docs/configuration/expected-outputs/python/)

**Failure shape:** `get_assert(output, context)` returns `bool`, `float`, or `{"pass": false, "score": 0, "reason": "..."}`.

**Our port:** `assert_*.py` modules per check family; `output` is JSON-serialized artifact; `reason` carries real diagnostic text (not a constant `assertion returned False`).

## Braintrust

**Docs:** [Writing scorers](https://www.braintrust.dev/docs/best-practices/scorers)

**Failure shape:** scorer returns `float` 0–1 or dict `{"name": ..., "score": 0}`; UI may show more metadata on full `Eval()`.

**Our port:** scorer functions on artifact dict; fail message `str({"key": "fXX_<lane>", "score": 0, ...})` with optional `comment` from check logic.

## Dependencies

| Package | In root `pyproject.toml` | Notes |
|---------|--------------------------|--------|
| `langsmith` | yes | evaluator-style functions |
| `braintrust` | yes | scorer-style functions |
| `promptfoo` | no | use programmatic `get_assert` pattern (no Node CLI required) |
| `pydantic-evals` | no | pytest-style inlined evaluators for parity with expressiveness |

## Artifact schema

See [`shared/artifact_io.py`](shared/artifact_io.py). Written by [`scripts/export_diagnostic_artifacts.py`](../scripts/export_diagnostic_artifacts.py) after fault-detection run with `TELCO_AGENT_TRACE_DIR` and `TELCO_STORE_SNAPSHOT_DIR` set.
