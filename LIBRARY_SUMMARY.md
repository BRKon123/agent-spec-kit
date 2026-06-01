# agent-spec-kit — Comprehensive Library Reference

**Version:** 0.1.0  
**Python:** ≥ 3.12  
**Package name:** `agent-spec-kit`  
**CLI entry point:** `agent-spec-kit` → `agent_spec_kit.cli:main`

This document is a single reference for everything the library provides: core APIs, matchers, generative testing (fuzz / simulate / shrink / extract), storage, CLI, web UI, integrations, examples, and bundled benchmarks. It is intended for readers who do not have the repository open.

---

## Table of contents

1. [What the library is](#1-what-the-library-is)
2. [Installation and optional extras](#2-installation-and-optional-extras)
3. [Core concepts](#3-core-concepts)
4. [Public Python API (`agent_spec_kit`)](#4-public-python-api-agent_spec_kit)
5. [Scenario DSL (`Scenario`)](#5-scenario-dsl-scenario)
6. [Decorators and discovery](#6-decorators-and-discovery)
7. [Fixtures and parametrization](#7-fixtures-and-parametrization)
8. [Repeats](#8-repeats)
9. [Agent contract and events](#9-agent-contract-and-events)
10. [Match system (`agent_spec_kit.match`)](#10-match-system-agent_spec_kitmatch)
11. [Match combinators (reference)](#11-match-combinators-reference)
12. [LLM criteria judges](#12-llm-criteria-judges)
13. [Fuzzing (`agent_spec_kit.fuzz`)](#13-fuzzing-agent_spec_kitfuzz)
14. [Shrinking (`agent_spec_kit.shrink`)](#14-shrinking-agent_spec_kitshrink)
15. [Regression extraction](#15-regression-extraction)
16. [Generative orchestration](#16-generative-orchestration)
17. [Runner, parallelism, and job results](#17-runner-parallelism-and-job-results)
18. [Failures and counterexamples](#18-failures-and-counterexamples)
19. [Counterexample detection](#19-counterexample-detection)
20. [State checks (`assert_that`)](#20-state-checks-assert_that)
21. [Structured output comparison](#21-structured-output-comparison)
22. [CLI (`agent-spec-kit`)](#22-cli-agent-spec-kit)
23. [Local result store](#23-local-result-store)
24. [Web API and results browser UI](#24-web-api-and-results-browser-ui)
25. [Framework integrations](#25-framework-integrations)
26. [Examples in the repository](#26-examples-in-the-repository)
27. [Benchmarks](#27-benchmarks)
28. [Development, testing, and UI build](#28-development-testing-and-ui-build)
29. [Module index](#29-module-index)

---

## 1. What the library is

**agent-spec-kit** is a **scenario-driven testing framework for LLM agents**. It sits in the same problem space as pytest-style tests, but is specialized for:

- Multi-turn conversations (agent and optional simulated user)
- Structured assertions on **outputs**, **tool calls**, and **environment state**
- **Normalized event traces** (agent turns, nested tools, subgraphs) independent of LangChain / Pydantic AI / custom stacks
- **Generative conversation testing**: fuzz user behaviour, simulate multi-turn dialogues, shrink failing inputs, and **extract** minimal regression scenarios to `.py` files
- **Persistent run history** (SQLite + compressed JSON blobs) browsable via CLI and a read-only **web UI**

Design principle: **policy and correctness are asserted in scenario oracles**, not hidden inside permissive tool simulators (see the telecom benchmark README for this split).

---

## 2. Installation and optional extras

### Base install

```bash
pip install agent-spec-kit
```

**Runtime dependencies:** `pydantic` (v2), `rich` (console output).

### Optional extras (`pyproject.toml`)

| Extra | Packages | Purpose |
|-------|----------|---------|
| `langchain` | `langchain`, `langchain-core`, `langgraph` | `wrap_langchain_agent` adapter |
| `pydantic-ai` | `pydantic-ai` | `wrap_pydantic_ai_agent` adapter |
| `ui` | `fastapi`, `uvicorn[standard]` | `agent-spec-kit ui` results browser |

### Dev dependency group (repo contributors)

Includes FastAPI, httpx, LangChain stack, `langchain-openai`, `pydantic-ai`, pytest, pytest-xdist, uvicorn.

### Expressiveness comparison group (not required for library use)

`langsmith`, `pydantic-evals`, `braintrust` — used only by `benchmarks/expressiveness/`.

---

## 3. Core concepts

| Concept | Description |
|---------|-------------|
| **Fixture** | `@fixture` function (sync, async, or `yield` teardown) registered in a global registry; may depend on other fixtures and `@parametrize` axes |
| **Scenario** | `@scenario` function with first parameter `s: Scenario`; queues steps then relies on `await s.materialise()` (often implicit via runner) |
| **AdaptedAgent** | Protocol: `async def run_turn(user_message: str) -> TurnResult` |
| **TurnResult** | `output`, `events`, `status`, `error` for one turn |
| **ConversationTurn** | One line in the transcript (`actor` = `"agent"` or `"user"`) |
| **JobResult** | Outcome of one scenario × param case × repeat index |
| **Experiment** | Named bucket for runs (`--experiment`); stable `experiment_id` derived from name |
| **Run** | One CLI invocation; stores git metadata, command line, summary |
| **Repeat** | One execution of a scenario case (scenarios can set `repeats=N`) |
| **Fuzz trial** | One generative attempt inside a `fuzz_conversation` step |
| **Failure signature** | `(check_kind, path, assertion_id)` used to match shrink candidates to the same failure |
| **Counterexample** | Structured failure payload for CLI/UI (matcher errors, transcript window, tool dicts) |

---

## 4. Public Python API (`agent_spec_kit`)

### Direct exports (`__init__.py`)

| Symbol | Role |
|--------|------|
| `AdaptedAgent`, `TurnResult`, `ConversationTurn` | Agent contract |
| `Scenario`, `create_scenario` | Scenario builder |
| `fixture`, `parametrize`, `scenario` | Registration decorators |
| `Case`, `case` | Parametrization values |
| `AgentEvent`, `AgentTurnEvent`, `ToolCallEvent`, `UserTurnEvent` | Event model |
| `new_event_id`, `collect_event_errors`, `print_rich_event_trace` | Event utilities |
| `Counterexample`, `FailureRecord`, `ScenarioAssertionFailed` | Failure types |
| `FuzzConfig`, `ShrinkConfig`, `ExtractionConfig` | Generative config |
| `__version__` | `"0.1.0"` |

### Lazy submodules (`__getattr__`)

| Name | Import path |
|------|-------------|
| `match` | `agent_spec_kit.match` |
| `fuzz` | `agent_spec_kit.fuzz` |
| `shrink` | `agent_spec_kit.shrink` |
| `wrap_langchain_agent` | `agent_spec_kit.integrations.langchain_adapter` |
| `wrap_pydantic_ai_agent` | `agent_spec_kit.integrations.pydantic_ai_adapter` |

Typical usage:

```python
import agent_spec_kit as ask
import agent_spec_kit.match as m

s = ask.create_scenario(agent)
s.user_message("Hello").assert_output(m.string(min_len=1))
await s.materialise()
```

---

## 5. Scenario DSL (`Scenario`)

`Scenario` is created via `create_scenario(adapted_agent, user=..., fixture_values=..., scenario_name=..., _case_values=...)`.

### Queued step methods (fluent API)

| Method | Behaviour |
|--------|-----------|
| `user_message(text)` | Routes to **agent** if both agent and user fixtures exist; else sole fixture. Queues a user line |
| `simulate_conversation(max_turns=..., stop_condition=..., stop_on_actor=..., seed_actor=..., seed_input=...)` | Multi-turn ping-pong; `stop_condition` is a matcher; `max_turns` counts simulation messages |
| `fuzz_conversation(fuzz_config=..., trials=..., max_user_turns=...)` | **Must not** run inside plain `materialise()` — only the generative orchestrator executes trials |
| `action(fn)` | Call fixture/env function with injected kwargs |
| `assert_that(fn)` | Same as action but labeled as assertion in results |
| `assert_output(matcher, turn="last"\|"up_to_now", actor=...)` | Match agent/user output |
| `assert_tool_calls(spec, ordered=..., allow_extras=..., turn=..., actor=...)` | Match normalized tool-call dicts |
| `forbid_tool_calls(spec, ordered=..., turn=..., actor=...)` | Negative tool assertion (distinct from empty `assert_tool_calls`) |

### Post-run checks (require completed `materialise`)

| Method | Sync/async |
|--------|------------|
| `check_output` / `async_check_output` | Inspect without raising |
| `check_tool_calls` / `async_check_tool_calls` | Inspect tool lists |
| `raise_unless_ok(result, actual=..., label=...)` | Turn `MatchResult` into `ScenarioAssertionFailed` |

### Param access inside scenario body

| Method | Returns |
|--------|---------|
| `s.param("axis_name")` | `Case.value` for parametrized axis |
| `s.case("axis_name")` | Full `Case` object |

### Properties

| Property | Meaning |
|----------|---------|
| `turn_results` | Immutable tuple of `ConversationTurn` |
| `last_turn` | Last turn (raises if empty) |
| `has_pending_steps` | Steps not yet executed |

### Recording mode

`_recording=True` makes `materialise()` a no-op so the generative probe can capture queued steps (including fuzz/simulate) without executing them.

### Helpers (module-level)

- `tool_dicts_from_turn_data(turn)` — tool dicts for matchers/UI from turn object or JSON dict
- `tool_dicts_from_transcript(transcript, turn_index=...)` — extract from serialized transcript
- `scenario_fuzz_metadata(s)` — introspect queued fuzz steps for storage

---

## 6. Decorators and discovery

### `@scenario`

```python
@scenario(
    agent_fixture="agent",           # and/or user_fixture="user_sim"
    repeats=1,
    tags=("pilot",),
    timeout_s=None,
    shrinking=ShrinkConfig(...),     # activated only with CLI --shrink
    extraction=ExtractionConfig(...), # activated only with CLI --extract
    regression_id=None,
)
def test_example(s, task, task_case): ...
```

**Rules:**

- At least one of `agent_fixture` or `user_fixture` required
- First parameter must be named `s`
- No `*args` / `**kwargs` on scenario callable
- Additional parameters are fixture names, parametrize axis names, or `{axis}_case` for full `Case`

### `@fixture` and `@parametrize`

- Fixtures register in `registries`; support dependency DAG via parameter names
- `@parametrize("name", values)` stacks on fixture (put `@fixture` **outer**, `@parametrize` **inner**)
- Fixtures may `yield` for teardown (reverse order after scenario)

### Discovery (`discovery.py`)

CLI `run PATH` collects:

- Single `.py` file, or
- Directory: all `test_*.py` and `fixtures.py` **recursively**

Each file is imported as a unique hashed module name so decorators run and populate registries.

---

## 7. Fixtures and parametrization

Fixtures are the **dependency-injection layer** for scenarios: they build agents, databases, seeded worlds, flags, and teardown hooks. The runner resolves them before the scenario body runs and always runs teardowns (even on failure).

### Registering fixtures

```python
@fixture
def store():
    db = TelcoStore.from_seed(...)
    yield db
    db.close()

@fixture
@parametrize("task", [case("T01", seed_t01), case("T02", seed_t02)])
def agent(task):
    return wrap_langchain_agent(build_graph(task), ...)
```

**Rules:**

- Put `@fixture` on the **outer** decorator; stack `@parametrize` **inside** (closer to the function).
- Fixture parameters must be other fixture names or `@parametrize` axis names — no `*args` / `**kwargs`.
- Return a plain value, `await` an async function, or `yield` for teardown.

### Dependency graph

`fixture_graph.resolve_fixtures(scenario, param_case=...)`:

1. Collects all fixtures needed by the scenario (`agent_fixture`, `user_fixture`, and any fixture names in the scenario signature).
2. **BFS-expands** transitive fixture dependencies (`dep_names` from each fixture’s signature).
3. **Topologically sorts** fixtures (cycle → `RuntimeError`).
4. Invokes fixtures in order, passing resolved dependencies as kwargs.

**Teardown order:** reverse of setup. Supports:

- `async def` fixtures
- sync fixtures returning awaitables
- `yield` / `async yield` generators (teardown runs after scenario completes or errors)

On setup failure, already-registered teardowns run before the exception propagates.

### Parametrization axes

`@parametrize("axis_name", values)` on a fixture defines a **Cartesian product axis**:

- Multiple axes on one fixture → all combinations of cases.
- Same axis name on different fixtures in one scenario graph → cases must be **identical** (same ids in same order) or resolution raises `ValueError`.

`scenario_case_runs(scenario)` returns `list[dict[str, Case]]` — one dict per combination. Example keys: `{"task": Case(...), "persona": Case(...)}`.

### Stable keys for storage and UI

| Helper | Example |
|--------|---------|
| `scenario_key("test_foo", {"task": case(...)})` | `test_foo[task=T01]` |
| `parameter_key({"task": case(...)})` | `task=T01` |
| CLI / UI `case_id` | `task=foo+persona=bar` |

### Wiring into scenarios

| Mechanism | How it reaches the scenario |
|-----------|----------------------------|
| `agent_fixture="agent"` | Resolved agent injected into `create_scenario(adapted_agent=...)` |
| `user_fixture="user_sim"` | Resolved user simulator for dual-actor scenarios |
| Scenario param `store` | Fixture value passed as `store` argument |
| Scenario param `task` | Param axis **value** (`Case.value`) |
| Scenario param `task_case` | Full **`Case`** object when the parameter is named `{axis}_case` |

Inside the scenario body, `s.param("task")` and `s.case("task")` read from `_case_values` without going through the function signature.

### `action` vs fixture injection

- **`s.action(fn)`** — calls `fn` with kwargs resolved from `fixture_values` (same name rules as fixtures).
- **`s.assert_that(fn)`** — same invocation path, but recorded as an **environment assertion** in results (`assertion_type` / `step_kind`).

Use fixtures for **setup**; use `assert_that` for **post-conditions** on env state (see [§20 State checks](#20-state-checks-assert_that)).

### Typical patterns

| Pattern | Example use |
|---------|-------------|
| Per-case DB | `@parametrize("task", cases)` + `store(task)` fixture with isolated SQLite |
| Shared agent | Single `agent` fixture, parametrized only on task seed |
| Env flags | `env_flag_true` fixture consumed by `assert_that` |
| Dual actors | `agent_fixture` + `user_fixture` for simulation studies |

---

## 8. Repeats

`@scenario(repeats=N)` runs the **same scenario case** `N` times as separate **repeat indices** (`1..N`). Each repeat is an independent `JobResult` with its own transcript blobs and status.

### Why repeats exist

- **Stochastic agents** — catch flaky failures across LLM/tool randomness
- **Fuzz trials are not repeats** — `fuzz_conversation(trials=M)` runs `M` trials *inside one repeat*; do not conflate with `repeats`
- **Aggregation** — `ScenarioResultRecord` stores `repeats_passed` / `repeats_failed`; run summary includes **repeat pass rate**

### Execution model

For each `(scenario, param_case)` the CLI builds `N` jobs:

```
test_foo[task=T01] [1/3]
test_foo[task=T01] [2/3]
test_foo[task=T01] [3/3]
```

With `-n 4`, repeats for **different** scenarios/cases may run in parallel in worker processes. `--fail-fast` stops after the first failing job globally (serializes workers).

### Storage and UI

- Each repeat → `repeat_results` row + gzip transcript/assertion blobs
- Run detail table shows **one row per repeat** (column “Repeat #”)
- Compare view uses the **latest** repeat per experiment when diffing cells

### Configuration

```python
@scenario(agent_fixture="agent", repeats=5, tags=("flaky",))
async def test_policy_stable(s): ...
```

`repeats` must be `>= 1` (default `1`). There is no built-in “pass if k-of-n” rule — you get `N` binary outcomes; analyze pass rate in the UI summary or external scripts.

### Interaction with generative steps

A scenario with `repeats=3` and `fuzz_conversation(trials=10)` executes **3 repeats**, each running **10 fuzz trials** (30 trials total per param case).

---

## 9. Agent contract and events

### `AdaptedAgent` (`run.py`)

Custom frameworks (CrewAI, etc.) implement:

```python
async def run_turn(self, user_message: str) -> TurnResult: ...
```

Populate `TurnResult.events` with typed events — **not** ad-hoc dicts. Prefer **coarse step-level** events over token streams.

### Event types (`events.py`)

| Class | Fields (high level) |
|-------|---------------------|
| `BaseEvent` | `turn_index`, `event_id`, `source_path`, `metadata`, `children` |
| `AgentTurnEvent` | `user_input`, `agent_output`, `error`; nested tools/subgraphs in `children` |
| `ToolCallEvent` | `tool_name`, `args`, `result`, `error` |
| `UserTurnEvent` | `content`, `error` (synthetic, for failure traces) |

Utilities:

- `new_event_id(prefix=...)` — opaque IDs
- `collect_event_errors(roots, include_tools=...)` — aggregate errors from tree
- `print_rich_event_trace(roots)` — Rich tree to terminal
- `to_rich_tree()` on `BaseEvent` — build Rich `Tree`

### LangGraph adapter note

Nested root `AgentTurnEvent` shells may be flattened in failure traces so tools appear directly under user lines (`failures.conversation_turns_to_event_trace`).

---

## 10. Match system (`agent_spec_kit.match`)

Import: `import agent_spec_kit.match as m`

### Entry points

| Function | Description |
|----------|-------------|
| `m.check(spec, actual)` | Sync validation → `MatchResult` |
| `m.async_check(spec, actual)` | Async (required for `llm_criteria`) |
| `m.match(spec, message=...)` | Build matcher without running |

### Coercion (`coerce_any`)

Literals, nested `dict`/`list`, `re.Pattern`, callables, and explicit `BaseMatcher` instances become matchers automatically.

### Scalar and structural matchers

| Matcher | Purpose |
|---------|---------|
| `m.string(min_len, max_len, pattern)` | String constraints |
| `m.number(min, max, int_only)` | Numeric constraints |
| `m.regex(...)` | Regular expression |
| `m.one_of(...)`, `m.all_of(...)`, `m.not_(...)`, `m.optional(...)` | Combinators |
| `m.any_value()` | Always passes |
| `m.contains(substr)` | Substring |
| `m.object({field: spec}, extra=...)` | Object shape; `extra` policy for unknown keys |
| `m.list([...], mode="ordered"\|"unordered", allow_extras)` | List matching |
| `m.list_of(inner)` | Homogeneous sequences |
| `m.tool_call(name, args=..., result=...)` | Single tool dict |
| `m.forbidden_tool_calls_matcher(...)` | Used by `forbid_tool_calls` |
| `m.transform(fn, inner)` | Map `actual` before inner match |
| `m.field`, `m.require`, `m.forbid` | Conditional rules with `.when(...)` on object fields |

### Tool-call list assertions

`assert_tool_calls` coerces specs to ordered/unordered list matchers over normalized dicts:

```python
{"name", "args", "result", "error", "children", "metadata"}
```

### Match results

- `MatchResult.ok` — boolean
- `MatchResult.errors` — list of `MatchError` with JSON-pointer-like `path`, codes, expected/actual snippets
- Errors fold into `Counterexample` on scenario failure

### Dataclass / Pydantic

Matchers work on dict views via `actual_as_mapping` (`dict`, `Mapping`, dataclasses, Pydantic `BaseModel`). JSON strings in agent output are **not** auto-parsed — use `m.transform(json.loads, m.object({...}))` when the wire format is a string.

---

## 11. Match combinators (reference)

This section documents **how combinators compose** and when to use each. All specs ultimately go through `coerce_any` unless you pass an explicit `BaseMatcher`.

### Coercion rules (`match/protocol.py`)

| Input | Becomes |
|-------|---------|
| `BaseMatcher` | unchanged |
| `dict` / `Mapping` | `m.object({k: coerce(v) ...})` (default `extra="forbid"` on inner object matcher) |
| `list` / `tuple` | `m.list([...], ordered, allow_extras=False)` — **fixed length** |
| `str`, `int`, `float`, `bool`, `None` | equality matcher |
| `re.Pattern` | `m.regex(pattern)` |
| User function/lambda (not a type) | `PredicateMatcher` with generic failure message |
| `m.match(fn, message="...")` | predicate with custom message |

### Logical combinators

| Combinator | Semantics | Typical use |
|------------|-----------|-------------|
| `m.all_of(a, b, c)` | AND — all must pass | Combine constraints on same value |
| `m.one_of(a, b, c)` | OR — first matching branch wins | Severity enums, alternate phrasings |
| `m.not_(inner)` | Negation | Forbidden substrings, anti-patterns |
| `m.optional(inner)` | `None` or missing key **or** `inner` matches | Optional JSON fields in `m.object` |

### Object shape (`m.object`)

```python
m.object(
    {"status": "ok", "count": m.number(min=1)},
    extra="forbid",   # reject unknown keys (default)
    rules=[...],      # conditional require/forbid
).where(lambda o: o["count"] < 100, "count must stay under cap")
```

| `extra` | Behaviour |
|---------|-----------|
| `"forbid"` | Any key not in `mapping` → `missing_key` / `extra_key` errors |
| `"ignore"` | Extra keys allowed (tool_call matcher uses this) |

**Conditional rules** (`match/rules.py`):

```python
m.require("pager_group").when(m.field("severity") == "high")
m.forbid("override_reason").when(m.field("source") == "logs")
```

`m.field("x")` supports `==`, `!=`, `<`, `<=`, `>`, `>=` against object fields.

**`.where(fn, message)`** — whole-object predicate after field checks (escape hatch for cross-field invariants).

### Lists

| API | Semantics |
|-----|-----------|
| `m.list([spec0, spec1], mode="ordered", allow_extras=False)` | Positional: i-th element matches i-th spec; lengths must match unless `allow_extras` |
| `m.list(..., mode="unordered")` | Each spec matches a **distinct** list item; order free |
| `m.list(..., allow_extras=True)` | Actual may be longer; specs match in order (ordered) or injectively (unordered) |
| `m.list_of(inner)` | Every element matches `inner` |

**Tool-call lists** — `assert_tool_calls([m.tool_call(...), ...])` uses list matching on normalized dicts. Use `ordered=False` for parallel sibling tools (see nested-tool oracle example).

### `m.tool_call` and nesting

```python
m.tool_call(
    "run_specialist",
    args={"query": m.contains("latency")},
    result=m.object({"score": m.number(min=0, max=1)}),
    children=[
        m.tool_call("pull_logs", args={...}),
        m.tool_call("score_anomaly", result=m.llm_criteria(...)),
    ],
)
```

Omitted keyword fields (`args`, `result`, `error`, `metadata`, `children`) are **unconstrained**. Nested `children` match subgraph tool events (LangGraph `subgraphs=True`).

### `m.transform`

```python
m.transform(json.loads, m.object({"status": "ok"}))
```

Runs `fn(actual)` before the inner matcher — essential when the agent returns **JSON as a string** but you want object matching.

### `m.contains` / `m.regex` / `m.string` / `m.number`

- `contains` — substring on `str(actual)`; case-insensitive by default
- `regex` — **full** string match (`fullmatch` semantics)
- `string` — length + optional embedded pattern
- `number` — range + optional `int_only`

### Embedding specs

Use `m.match(spec)` when you need a `BaseMatcher` instance inside another combinator without evaluating early. Use `m.match(lambda x: ..., message="...")` for documented predicate failures.

### Paths and errors

Failed checks attach a **path** like `$`, `$.itinerary[0].day`, `$.args.ticket.id`. `path_to_str` renders these for counterexamples. `MatchError.witness_json` may carry machine-readable extras (list length mismatches, etc.).

---

## 12. LLM criteria judges

### `m.llm_criteria(...)`

- **Async only** — use `await s.materialise()` or `await s.async_check_output(...)`
- `model` must be provider-prefixed: `openai:gpt-5-nano`, `anthropic:claude-sonnet-4-5`
- `criteria`: list of pass/fail rubric strings
- `threshold`: minimum criteria that must pass (default: all)
- `judge_context`: optional extra context for the judge
- `judge_fn`: inject custom sync/async backend `(actual, criteria, judge_context) -> LLMCriteriaJudgeResult | dict`

### Judge stack (`judges/`)

| Module | Role |
|--------|------|
| `router.judge_criteria` | Routes by provider prefix |
| `openai_judge` / `anthropic_judge` | Provider implementations |
| `structured.call_structured` | Pydantic JSON parsing (also used by fuzz `llm_mutations`) |
| `base.LLMCriteriaJudgeResult` | Structured per-criterion judgements |

**Guidance:** Prefer pass/fail criteria over numeric scores for stable judge outputs.

---

## 13. Fuzzing (`agent_spec_kit.fuzz`)

### `FuzzConfig`

```python
FuzzConfig(
    strategy=...,           # implements Strategy protocol
    seed_inputs=(),         # required for llm_mutations
    seed=42,                # optional RNG seed
)
```

### `UserAction` and `fuzz.user_action(...)`

Weighted behavioural intents with template strings for `behaviour_grammar`.

### Strategies

| Strategy | Module | `eager_generation` | Behaviour |
|----------|--------|-------------------|-----------|
| `behaviour_grammar(actions)` | `fuzz/behaviour_grammar.py` | **True** | Weighted random `UserAction` + template per turn; ignores transcript context |
| `hybrid(s1, (s2, w), ...)` | `fuzz/hybrid.py` | Inherited | Pick one inner strategy by weight per trial |
| `llm_mutations(model=...)` | `fuzz/llm_mutations.py` | False | LLM rewrites `seed_inputs`; uses structured judge stack |

### `Strategy` protocol (`fuzz_types.py`)

```python
async def generate(
    self, *, rng, max_user_turns, seed_inputs, context: FuzzSegmentContext | None
) -> Sequence[GeneratedTurn]
```

`GeneratedTurn`: `message`, `label`, `detail` dict.

### Context (`fuzz_context.py`)

Non-eager strategies receive `FuzzSegmentContext` built from prior transcript (agent outputs, tool summaries) so mutations can be context-aware.

### Fuzz driver (`fuzz/driver.py`)

- `FuzzerDriver` / `RandomBatchFuzzerDriver`
- `pick_fuzzer_driver` — concurrent trial scheduling (`asyncio.gather`)

### Trial metadata (`fuzz/summary.py`)

`render_trial_summary` — human-readable trial labels stored as `summary_label`.

### Scenario integration

`s.fuzz_conversation(..., trials=N, max_user_turns=M)` queues a step replaced at runtime with `N` independent user-message sequences. Uniform `trials` required across all fuzz steps in one scenario.

---

## 14. Shrinking (`agent_spec_kit.shrink`)

Activated by **CLI `--shrink`** and `@scenario(shrinking=ShrinkConfig(...))`.

### `ShrinkConfig`

| Field | Default | Meaning |
|-------|---------|---------|
| `passes` | (required) | Tuple of `ShrinkPassSpec` |
| `confirm_runs` | 3 | Re-runs per candidate to confirm same failure signature |
| `min_reproductions` | 2 | Minimum confirmations required |

### Pass builders

| Function | Kind | Behaviour |
|----------|------|-----------|
| `shrink.remove_user_turns()` | `remove_user_turns` | Delta-debug: try dropping one user line at a time |
| `shrink.simplify_user_messages()` | `simplify_user_messages` | Deterministic trim/case variants |
| `shrink.llm_semantic_simplify(model=..., candidates_per_message=5, ...)` | `llm_semantic_simplify` | LLM proposes shorter messages; engine verifies reproduction |

### Engine (`shrink_engine.py`)

`shrink_user_turns` applies passes in order; each candidate verified via `verify_shrink_candidate_async` (re-runs scenario, checks `FailureSignature`).

Shrink can run in **process pool** (`ShrinkVerifyJob`) for isolation.

### Simulate-only shrink

Scenarios with `simulate_conversation` but no fuzz: probe mode `simulate_only`, `trials_total=1`, captured user turns fed to shrink/extract.

---

## 15. Regression extraction

Activated by **CLI `--extract`** and `@scenario(extraction=ExtractionConfig(...))`.

### `ExtractionConfig`

| Field | Options |
|-------|---------|
| `target_file` | Path to append generated `@scenario` function |
| `mode` | `"append_scenario"` |
| `duplicate_policy` | `skip`, `replace`, `append_variant`, `error` |
| `assertion_policy` | `failed_only`, `all_after_fuzz` |
| `add_tags` | Tags on generated scenario |

### Implementation (`extraction_impl.py`)

- AST-parses source scenario
- Emits new function with concrete `user_message` steps + assertions
- **Fingerprint** deduplication per target file
- Status: `written`, `partial`, `noop`, `errored`, `skipped_duplicate`

### CLI

```bash
agent-spec-kit regressions <run_id>
```

Lists `RegressionExtractionRecord` rows from SQLite.

---

## 16. Generative orchestration

### Probe (`isolated_generative.probe_generative_scenario`)

1. Run scenario with `_recording=True`
2. Detect `fuzz_conversation` / `simulate_conversation` steps
3. Validate uniform trial counts
4. Pre-generate user messages for eager strategies
5. Return `ProbeResult` (mode, steps, phase errors, param labels)

### Full repeat (`run_full_generative_repeat`)

1. For each trial: merge generated user turns into step list
2. Run `materialise()` (inline or `FuzzTrialJob` in worker process)
3. Collect failure signatures, transcripts, behaviour labels
4. Optional shrink per failing trial
5. Optional extract → write regression file + DB record

### `FailureSignature` (`generative.py`)

Identifies **which assertion failed** so shrink does not accept candidates that fail differently.

### Progress

CLI emits `progress: <scenario> [<repeat>/<total>]: <message>` including heartbeat every 60s for long-running jobs.

---

## 17. Runner, parallelism, and job results

### `run_scenario_job`

Standard path: resolve fixtures → `create_scenario` → call scenario fn → `materialise()` → teardown.

### Worker jobs (picklable for `ProcessPoolExecutor`)

| Job | Purpose |
|-----|---------|
| `ScenarioRepeatJob` | Full non-generative repeat in worker |
| `FuzzTrialJob` | Single fuzz trial in worker |
| `ShrinkVerifyJob` | Shrink candidate verification in worker |

### CLI parallelism (`-n`)

| Value | Meaning |
|-------|---------|
| `1` | Inline executor (same code path, no fork) |
| integer | `ProcessPoolExecutor(max_workers=n)` |
| `auto` | `os.cpu_count()` |
| `logical` | Logical CPUs when `psutil` available |

`--fail-fast` forces serial execution (ignores `-n`).

### `JobResult` fields (selected)

| Field | Content |
|-------|---------|
| `ok`, `status`, `detail` | Pass/fail summary |
| `scenario_name`, `case_id`, `repeat_index`, `repeat_total` | Identity |
| `param_cells` | Human param labels for tables |
| `turn_results`, `assertions` | Transcript and per-assertion records |
| `counterexample` | Structured failure |
| `fuzz_trials` | List of trial dicts when generative |
| `fuzz_config_json` | Serialized fuzz config |
| `shrink_result` / `shrink_results` | Shrink outcomes |
| `regression_extraction` | Extract status dict |
| `phase_errors` | Probe/fuzz/shrink/extract errors |
| `failure_kind`, `failure_message` | Top-level classification |
| `duration_s`, timestamps | Timing |

---

## 18. Failures and counterexamples

### `ScenarioAssertionFailed`

Raised when matchers fail; caught by runner into `JobResult`.

### `Counterexample`

Includes:

- Matcher errors with paths
- Transcript window (last N agent turns with interleaved user lines)
- Tool dict snapshots
- Event trace roots for Rich / UI (`conversation_turns_to_event_trace`)

### CLI failure display (`cli_reporting.py`)

- `emit_failure_detail` — panel with counterexample, Rich event tree, assertion breakdown
- `emit_trial_failure_detail` — per fuzz trial failures
- `emit_summary_table` — pass/fail grid with dynamic param columns
- `emit_job_compact` — live progress line per repeat

Mirrors much of what the **Trace drawer** shows in the UI.

For the full detection pipeline (`FailureRecord` → `counterexample_from_failure`, paths, witnesses, fuzz signatures), see [§19 Counterexample detection](#19-counterexample-detection).

---

## 19. Counterexample detection

A **counterexample** is the library’s structured explanation of *why* a scenario failed. It is built automatically — you do not construct it manually in tests.

### Pipeline

```
assert_output / assert_tool_calls / forbid_* / simulate stop_condition
        ↓
match.async_check → MatchResult (errors with paths)
        ↓
raise_scenario_match_failure → FailureRecord + ScenarioAssertionFailed
        ↓
counterexample_from_failure(record) → Counterexample
        ↓
CLI Rich panel / SQLite blob / UI FailureCard
```

For `assert_that` and bare `AssertionError`, the record has `matcher_errors=()` and the message comes from the Python exception.

### `FailureRecord` fields

| Field | Role |
|-------|------|
| `scenario_name`, `step_index`, `step_kind` | Where (`assert_output`, `assert_tool_calls`, `assert_that`, `agent_error`, …) |
| `turn_index`, `turn_results` | Which conversation turn |
| `assertion_index_after_turn` | 1st, 2nd, … assertion after same turn |
| `matcher_errors` | All `MatchError` from matcher |
| `actual` | Raw compared value (output, tool list, etc.) |
| `events` | Optional event snapshot |

### `Counterexample` payload

| Field | Content |
|-------|---------|
| `headline` | `scenario_name: <primary message>` |
| `location` / `location_detail` | Human step/turn description (“assert_tool_calls after turn #2 (agent turn)”) |
| `path` | Deepest mismatch path (e.g. `$.args.ticket.id`) |
| `expected_summary` | Short expected side |
| `actual_min` | Full actual for UI scroll (tool lists not truncated) |
| `notes` | Extra errors, list-length hints, “+N more matcher errors” |
| `events` | Rich trace roots (`conversation_turns_to_event_trace`) |

### Matcher failure selection

When multiple `MatchError` exist:

- **Headline** uses the first error; if a **deeper path** exists, message becomes `outer; mismatch at $.foo: inner`
- **Deepest path** (`max(..., key=len(path))`) drives `path` and witness parsing
- **Witness JSON** on errors can include `actual_witness` for precise sub-values

### Agent/runtime errors

`collect_agent_errors` gathers:

- `error` fields on tool dicts and event trees
- Heuristic text that looks like exceptions (not tool-call JSON dumps)

Used when `step_kind == "agent_error"` or to enrich notes.

### Transcript window

Failure traces include at most the last **5 agent turns** (plus interleaved user lines) to keep panels readable — full transcript remains in stored blobs.

### Fuzz trials

Each failing fuzz trial gets its own counterexample blob (`counterexample_blob_path` on `FuzzTrialRecord`). CLI `emit_trial_failure_detail` prints them after the repeat-level summary.

### Failure signatures (generative)

For shrink, the first failing trial’s assertion identity is hashed into `FailureSignature` (`check_kind`, `path`, `assertion_id`) so shrunk inputs must reproduce the **same** failure, not merely “still fail somehow.”

---

## 20. State checks (`assert_that`)

**State checks** validate **environment / database / fixture state** after (or between) conversation steps. They are the right tool when correctness is not visible in the final assistant string or tool list alone.

### API

```python
s.assert_that(check_store_unchanged)
# or
s.assert_that(lambda: oracles.assert_no_credit_rows(store))
```

- Callable is invoked with **fixture kwargs** (same resolution as `s.action(fn)`).
- May be sync or async; may use plain `assert` / `pytest`-style checks.
- Recorded as `step_kind="assert_that"` in failures and assertion tables.

### vs other assertion types

| Mechanism | Inspects | Oracle type (telecom bench) |
|-----------|----------|----------------------------|
| `assert_output` | Agent/user text or structured output | **O** (output) |
| `assert_tool_calls` / `forbid_tool_calls` | Normalized tool trace | **T** (trace) |
| `assert_that` | DB rows, files, auth flags, custom env | **S** (state) |
| `action` | Side effect only (no pass/fail) | — |

TelcoSupportBench policy **P1–P10** is enforced in scenario oracles — especially `assert_that` helpers in `benchmarks/telecom_support/tasks/specs/oracles.py` (e.g. `assert_p2_credit_policy`, `assert_no_mutations`, `assert_authenticated`). Tools stay permissive; violations surface here.

### Patterns

**1. Dedicated oracle module**

```python
# oracles.py
def assert_no_sim_orders(store: TelcoStore) -> None:
    assert count_sim_orders(store) == 0, f"expected zero sim orders, found {n}"

# scenario
s.assert_that(lambda: oracles.assert_no_sim_orders(store))
```

**2. Fixture-returned check function**

```python
def function_checks_store(store):
    assert store.ticket_count() == 1

s.assert_that(function_checks_store)
```

**3. Parametrized store per task**

```python
@fixture
@parametrize("task", TASK_CASES)
def store_us(task):
    return TelcoStore.from_seed(task.value)

s.assert_that(lambda: o.assert_no_profile_read_before_auth(store_us))
```

### Failure counterexamples

`assert_that` failures usually have **no matcher path**. Counterexample shows:

- `expected_summary`: assert message or “assert_that failed”
- `actual_min`: often “No structured value (fixture/env assertion only)” unless the callable returned `False` or left structured `actual` on the record

### Ordering

Steps run in queue order. Common pattern:

```python
s.user_message("...").assert_output(...).assert_tool_calls(...).assert_that(check_db)
await s.materialise()  # when using deferred asserts in scenario body
```

Queued `assert_that` runs **during** `materialise` at its step index — place it after the turns whose side effects you inspect.

---

## 21. Structured output comparison

Agents that return **JSON / dict-shaped** outputs (including LangGraph `response_format`, tool-free structured replies, or hardcoded adapters) are asserted with **`assert_output`** + object matchers — not string contains.

### Wire formats

| Agent returns | Matcher approach |
|---------------|------------------|
| `dict` / Pydantic model | `m.object({...})` directly |
| JSON string | `m.transform(json.loads, m.object({...}))` |
| Plain text with JSON substring | `m.contains` or extract via `transform` |

The hardcoded example (`examples/hardcoded_structured_output/`) uses a dict-returning adapter so `assert_output(m.object({...}))` applies without `json.loads`.

### Example: nested object + homogeneous list

```python
s.assert_output(
    m.object(
        {
            "status": "ok",
            "task": "plan_trip",
            "destination": "Lisbon",
            "days": 3,
            "itinerary": m.list_of(
                m.object({
                    "day": m.number(int_only=True),
                    "activity": m.string(min_len=3),
                })
            ),
        },
        extra="forbid",
    )
)
```

- **`extra="forbid"`** — agent must not invent extra top-level keys (strict schema).
- **`m.list_of`** — every itinerary element matches the same shape.
- Literal `"Lisbon"` — exact equality on that field.

### Structured fields inside tool calls

Structured **tool results** use `m.tool_call(..., result=m.object({...}))` or `result=m.llm_criteria(...)` when the result is prose but must satisfy a rubric:

```python
m.tool_call(
    "score_anomaly",
    result=m.llm_criteria(
        criteria=["mentions numeric score", "does not claim certainty"],
        threshold=2,
        model="openai:gpt-5-nano",
    ),
)
```

Nested-tool oracle (`examples/langchain_nested_tool_oracle/`) combines:

- `args=m.object({...}, rules=[m.require(...).when(...)])` on structured tool inputs
- `children=[...]` for subgraph tools
- `m.list(..., mode="unordered")` for component lists
- LLM rubrics on specialist **results**

### LangGraph structured specialists

When subgraphs use `response_format=SomeModel`, the adapter maps model output into tool/turn events; oracles still target **normalized tool dicts** or final coordinator text. Do not match raw message chunks.

### Partial / evolving schemas

| Need | Combinator |
|------|------------|
| Optional field | `m.optional(m.string())` |
| One of several statuses | `m.one_of("ok", "degraded")` |
| Unknown extra metadata OK | `extra="ignore"` on that object only |
| Field only when condition holds | `rules=[m.require("x").when(m.field("y") == "z")]` |

### `turn="up_to_now"`

For multi-step structured outputs, `assert_output(spec, turn="up_to_now", actor="agent")` concatenates all agent outputs so far (newline-separated) before matching — useful when the final message summarizes earlier structured turns.

### Comparison vs plain JSON equality

| Approach | When |
|----------|------|
| `assert_output(m.object({...}))` | Schema, tolerances, optional fields, LLM judges on subfields |
| `assert_output('{"status":"ok"}')` | Exact string (brittle) |
| `m.transform(json.loads, m.object(...))` | String wire format |

Structured comparison failures produce **path-qualified** counterexamples (`$.itinerary[1].day`), which is critical for debugging long JSON outputs in the UI trace drawer.

---

## 22. CLI (`agent-spec-kit`)

### Commands

| Command | Description |
|---------|-------------|
| `run PATH` | Discover and execute scenarios; persist to `.agent_spec_kit/` |
| `runs` | List last 20 runs (id, experiment, status, scenario counts, started_at) |
| `show RUN_ID` | Run summary + deduplicated failure messages |
| `regressions RUN_ID` | List regression extractions |
| `ui` | Serve FastAPI + SPA (requires `[ui]` extra) |
| `clear` | Delete entire local store (interactive `yes` or `-y`) |

### `run` flags

| Flag | Effect |
|------|--------|
| `PATH` | File or directory |
| `--tags a,b` | Scenario must have **any** listed tag |
| `--tags-all a,b` | Scenario must have **all** listed tags |
| `--list` | Print discovered scenarios table; exit 0 |
| `--fail-fast` | Stop after first failure |
| `-n num\|auto\|logical` | Worker processes (default 1) |
| `--experiment NAME` | Experiment name (default `default`) |
| `--metadata key=value` | Repeatable run metadata |
| `--notes TEXT` | Free-text run notes |
| `--shrink` | Enable per-scenario `ShrinkConfig` after fuzz failures |
| `--extract` | Enable per-scenario `ExtractionConfig` |

### `ui` flags

| Flag | Default | Effect |
|------|---------|--------|
| `--host` | `127.0.0.1` | Bind address |
| `--port` | `8765` | Port |
| `--open` | off | Open browser |
| `--no-frontend` | off | API only (for Vite dev proxy) |

### Git metadata

Automatically recorded: `git_commit`, `git_branch`, `git_dirty` via subprocess.

### Exit codes

- `0` — all jobs passed (or `--list` success)
- `1` — one or more failures, or user aborted `clear`
- `2` — usage / path / import errors

---

## 23. Local result store

### Layout

Default root: **`.agent_spec_kit/`** (override via `StorageConfig.root`)

```
.agent_spec_kit/
  results.sqlite
  blobs/{run_id}/
    {repeat_id}_transcript.json.gz
    {repeat_id}_assertions.json.gz
    {repeat_id}_counterexample.json.gz
    {repeat_id}_trial{NNNN}_transcript.json.gz
    ...
```

### SQLite tables

| Table | Contents |
|-------|----------|
| `experiments` | experiment_id, name |
| `runs` | run header, git, command, notes, metadata_json, summary_json, status |
| `scenario_results` | Per scenario×case aggregates, tags, fuzz_config_json |
| `repeat_results` | Per repeat status, duration, blob paths |
| `assertions` | Per-assertion status, type, details, counterexample blob |
| `fuzz_trials` | trial index, seeds, user_turns, behaviour_labels, failure_signature, per_step_user_turns |
| `shrink_results` | passes applied, original/shrunk turns, candidate count |
| `regression_extractions` | target file, function name, fingerprint, status |
| `phase_errors` | phase ∈ fuzz/shrink/extract, error_kind, message |

### `LocalResultStore` (`result_store.py`)

CRUD for all record types, `compute_run_summary`, `compare_experiments_most_recent`, blob read/write via `write_json_blob` / `read_json_blob`.

### Run summary metrics

Includes scenario/repeat pass rates, duration percentiles, failure kind breakdowns, fuzz/regression counts (used in UI columns).

---

## 24. Web API and results browser UI

### Serving

```bash
pip install 'agent-spec-kit[ui]'
agent-spec-kit ui --open    # http://127.0.0.1:8765
```

- FastAPI app (`web/server.py`) mounts SPA from `web/dist/`
- CORS allows Vite dev origin `http://localhost:5173`
- Missing bundle → API-only mode with warning

### REST API (`/api`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | `{status: "ok"}` |
| GET | `/experiments` | All experiments with run counts |
| GET | `/runs` | Paginated runs (`experiment_id`, `status`, `limit`, `offset`) |
| GET | `/runs/{run_id}` | Full run detail + metadata + summary |
| GET | `/runs/{run_id}/scenarios` | Scenario rows with nested repeats |
| GET | `/runs/{run_id}/fuzz-trials` | All fuzz trials for run |
| GET | `/fuzz-trials/{trial_id}` | Trial detail + transcript (loaders) |
| GET | `/runs/{run_id}/regressions` | Regression extraction rows |
| GET | `/repeats/{repeat_result_id}/trace` | Transcript, assertions, counterexample, fuzz trial index |
| GET | `/compare?experiments=A,B,C&strategy=most_recent` | Cross-experiment grid |

**Errors:** `application/problem+json` (RFC 7807) via `ProblemDetail` schema.

**Compare:** Requires ≥2 unique experiment IDs; `strategy=most_recent` only. Returns `excluded_fuzz_scenarios` when scenario keys only exist in fuzzed form (not comparable across experiments).

### Frontend stack

- React 18, React Router, TanStack Query, Tailwind, shadcn-style components, Sonner toasts, Lucide icons

### Routes

| Path | Page |
|------|------|
| `/` | **Runs list** — filters by experiment/status, sortable table, column picker |
| `/runs/:runId` | **Run detail** — scenario/repeat table, side panels, trace drawer |
| `/compare` | **Compare** — multi-experiment diff (`?experiments=A,B,C`) |
| `*` | Not found |

### Runs list page features

- Column picker with persistence (`localStorage` key `ask.runs.columnVisibility`)
- Base columns: experiment, run id, status, scenarios passed/total, failed count, repeat pass rate, durations, timestamps
- Dynamic columns for any `summary.*` and `metadata.*` keys seen in data

### Run detail page features

- **Scenario table**: per-repeat rows; click opens trace drawer (prefers failing repeat)
- **Column picker** (`ask.scenarios.columnVisibility`) including dynamic `param:{axis}` columns
- **Run side panel** (collapsible): summary, git info, metadata, failure-kind/tag/parameter breakdowns
- **Fuzz trials panel** + **Fuzz trial side panel**: browse trials; open trial-specific trace
- Links back to runs list

### Trace drawer

- Resizable right panel (drag handle, 420px–viewport width)
- Loads `/api/repeats/{id}/trace` or fuzz trial detail
- **TraceTree**: nested collapsible event tree
- Per-node field toggles for `args`, `result`, `input`, `output`, `metadata` (scroll-capped JSON via `JsonView`)
- **FailureCard**: mirrors CLI failure box (matcher errors, counterexample)
- **FuzzTrialTraceContent**: trial-specific layout; link from repeat trace to individual trials
- Phase errors section when present

### Compare page features

- Add/remove experiment slots (no duplicates)
- URL sync: `/compare?experiments=A,B,C`
- Defaults to two most recent experiments when empty
- Row = scenario key; cells = per-experiment latest repeat status, repeats, duration, failure kind/message
- **Mismatch highlighting** (amber) when status differs across experiments
- Column picker for row vs per-experiment cell fields
- Click cell → trace drawer for that repeat
- Banner when `excluded_fuzz_scenarios` returned from API

### API client (`frontend/src/api/`)

- `http.ts` — `ApiError` with parsed problem details
- `queries.ts` — React Query hooks: `useRuns`, `useRun`, `useScenariosForRun`, `useRepeatTrace`, `useFuzzTrialsForRun`, `useFuzzTrial`, `useCompare`, `useExperiments`

### Build / dev

```bash
./scripts/build_ui.sh              # production bundle → src/agent_spec_kit/web/dist/
./scripts/build_ui.sh --ci         # CI mode before wheel build

# Dev loop:
uv run agent-spec-kit ui --port 8765 --no-frontend &
npm --prefix frontend run dev      # http://localhost:5173 proxies /api
```

---

## 25. Framework integrations

### LangChain / LangGraph (`wrap_langchain_agent`)

```python
from agent_spec_kit.integrations.langchain_adapter import wrap_langchain_agent

adapted = wrap_langchain_agent(
    graph,
    lambda msg: {"messages": [HumanMessage(content=msg)]},
    stream_mode="updates",
    version="v2",
    subgraphs=True,
    context=...,
    config=...,
)
result = await adapted.run_turn("Hello")
```

- Streams via `graph.astream`
- `UpdatesNormalizer` maps chunks → `AgentTurnEvent` tree with nested `ToolCallEvent`
- Supports `stream_mode`, `version`, `subgraphs` (forwarded to LangGraph)
- `context` / `config` (or callables `str → value`) for per-turn LangGraph runtime — **not** the same as stream options

### Pydantic AI (`wrap_pydantic_ai_agent`)

```python
adapted = wrap_pydantic_ai_agent(agent, deps=..., **run_kwargs)
```

- Maps `AgentRunResultEvent`, `FunctionToolCallEvent`, `FunctionToolResultEvent`
- Filters to agent's registered function tool names

Both set `TurnResult.output`, `events`, `status`, and aggregate errors.

---

## 26. Examples in the repository

| Directory | Demonstrates |
|-----------|--------------|
| `examples/langchain_scenario_tests/` | Basic LangGraph scenarios |
| `examples/langchain_multiply_dialog/` | Multi-turn dialog |
| `examples/langchain_counterexample_demo/` | Counterexample / failure panels |
| `examples/langchain_arithmetic_llm_checks/` | `llm_criteria` matchers |
| `examples/langchain_sql_json_store/` | Tool + state assertions |
| `examples/langchain_nested_tool_oracle/` | Nested `m.tool_call(..., children=[...])` |
| `examples/langchain_fuzz_demo/` | **Fuzz + shrink + extract** end-to-end (see README) |
| `examples/hardcoded_structured_output/` | Structured output without live LLM |
| `examples/event_printing/` | `langchain_run_turn.py`, `pydantic_run_turn.py`, nested event demos |

### langchain_fuzz_demo highlights

- `behaviour_grammar` strategy
- `ShrinkConfig` + `ExtractionConfig` on `@scenario`
- `--shrink`, `--shrink --extract`
- Regressions written to `regressions/extracted.py` (gitignored)
- UI: fuzz trials table, phase errors, compare exclusion banner

---

## 27. Benchmarks

### `benchmarks/telecom_support/` (TelcoSupportBench)

Mobile-network customer-support benchmark:

- **Coordinator** + **NetworkDiagnosticsSpecialist** + **BillingPolicySpecialist** (LangGraph, `subgraphs=True`)
- Permissive SQLite tools; policy in `policy.md`; oracles in scenarios (O/S/T/F)
- Tasks T01–T50 catalog in `tasks/catalog.py`
- Run: `agent-spec-kit run benchmarks/telecom_support/ --tags pilot,reference`
- Parallel: `-n 4` safe (isolated DB per job via fixtures)

**Sub-studies (scripts, not part of core library API):**

| Study | Scripts | Artifacts |
|-------|---------|-----------|
| Fault detection F01–F10 | `run_fault_detection.py`, `bootstrap_fault_detection.py` | `tasks/fault_detection/` |
| User simulation | `run_user_simulation_study.py` | `tasks/user_simulation/` |
| Fuzzing study | fuzz scenario tests + `fuzzing_study_lib.py` | `tasks/fuzzing/` |
| Shrinking study | `run_user_sim_shrink_study.py` | `tasks/shrinking/` |
| Extraction study | `run_user_sim_extraction_study.py` | `tasks/extraction/` |
| Regressions | extracted scenario modules | `tasks/regressions/` |

### `benchmarks/expressiveness/`

Authoring-effort comparison: **12 check types (C01–C12)** implemented in agent_spec_kit, plain pytest, LangSmith-style, Pydantic Evals, Promptfoo, Braintrust.

- Frozen traces in `traces/` for CI without API keys
- `CANONICAL_SPEC.md`, `generate_table.py` → `EXPRESSIVENESS_TABLE.md` (LOC + failure specificity rubrics)
- Run: `agent-spec-kit run benchmarks/expressiveness/ --tags expressiveness`

---

## 28. Development, testing, and UI build

### Test layout (`tests/`)

| Area | Files |
|------|-------|
| Match | `tests/match/test_*.py` — object, list, regex, transform, forbidden, llm router, dataclass |
| Scenarios | `test_scenario.py`, `test_simulation_scenario.py`, integration features |
| Fuzz/shrink | `test_fuzzing_study.py`, `test_llm_semantic_simplify.py`, segment context |
| CLI/store | `suite/test_cli_smoke.py`, `test_result_store.py`, `test_cli_clear.py`, blob paths |
| Web | `test_web_loaders.py` |
| Integrations | `integration/test_langchain_live.py`, `test_pydantic_ai_live.py` (marked `integration`) |

### Pytest defaults

```ini
addopts = -m 'not integration'
```

Run live integration tests:

```bash
uv run pytest --override-ini addopts= -m integration
```

### Environment (direnv)

Repo supports `.envrc` + `.env` for `OPENAI_API_KEY` (see root `README.md`).

### Package build

- Build backend: `uv_build`
- Wheel includes prebuilt `web/dist/` when `./scripts/build_ui.sh --ci` ran before `uv build`

---

## 29. Module index

| Path | Responsibility |
|------|----------------|
| `__init__.py` | Public exports and lazy loaders |
| `run.py` | `AdaptedAgent`, `TurnResult`, `ConversationTurn` |
| `scenario_core.py` | `Scenario` DSL and step execution |
| `runner.py` | `JobResult`, `run_scenario_job`, worker entrypoints |
| `generative.py` | `FailureSignature`, `CapturedEpisode` |
| `isolated_generative.py` | Probe, fuzz trials, shrink/extract orchestration |
| `decorators.py` | `@fixture`, `@parametrize`, `@scenario` |
| `discovery.py` | Path collection and dynamic import |
| `registries.py` | In-memory fixture/scenario registry |
| `fixture_graph.py` | DAG resolution, param Cartesian product |
| `param_cases.py` | `Case`, `case` |
| `events.py` | Event dataclasses and Rich helpers |
| `failures.py` | Counterexamples and trace conversion |
| `fuzz_config.py` | `FuzzConfig`, `ShrinkConfig`, `ExtractionConfig`, `UserAction` |
| `fuzz_types.py` | `Strategy`, `GeneratedTurn`, `FuzzSegmentContext` |
| `fuzz_context.py` | Transcript → segment context |
| `fuzz/__init__.py` | Public fuzz API |
| `fuzz/behaviour_grammar.py` | Weighted template strategy |
| `fuzz/hybrid.py` | Weighted strategy mix |
| `fuzz/llm_mutations.py` | LLM mutation strategy |
| `fuzz/driver.py` | Trial drivers |
| `fuzz/summary.py` | Trial summary strings |
| `shrink/__init__.py` | Shrink pass builders |
| `shrink/llm_simplify.py` | LLM simplification pass |
| `shrink_engine.py` | Shrink search + verify loop |
| `extraction.py` | Extraction facade |
| `extraction_impl.py` | AST regression writer |
| `match/*` | Matcher implementations |
| `judges/*` | LLM criteria providers |
| `integrations/langchain_adapter.py` | LangGraph adapter |
| `integrations/pydantic_ai_adapter.py` | Pydantic AI adapter |
| `cli.py` | CLI main, persistence, orchestration |
| `cli_reporting.py` | Rich tables and failure panels |
| `console_format.py` | Value formatting for terminal |
| `parallel_workers.py` | `-n` flag resolution |
| `result_store.py` | SQLite store |
| `storage_records.py` | Typed records and key helpers |
| `web/server.py` | FastAPI app factory |
| `web/api.py` | REST routes |
| `web/loaders.py` | Trace/trial payload builders |
| `web/schemas.py` | Pydantic response models |
| `web/dist/` | Built SPA assets |

---

## Quick reference: end-to-end fuzz workflow

```bash
# 1. Define scenario with fuzz + shrink + extract configs
# 2. Run with flags
OPENAI_API_KEY=... agent-spec-kit run path/to/tests/ --shrink --extract -n 4

# 3. Inspect
agent-spec-kit runs
agent-spec-kit show <run_id>
agent-spec-kit regressions <run_id>
agent-spec-kit ui --open

# 4. Compare experiments in UI
# /compare?experiments=default,experiment_b
```

---

*This file is generated as project documentation. For the latest API, prefer docstrings in `src/agent_spec_kit/` and the root `README.md` for install quick-start.*
