# TelcoSupportBench

Mobile-network customer-support benchmark for **agent-spec-kit**: coordinator + two specialist subgraphs, permissive SQLite tools, policy in [`policy.md`](policy.md), compliance judged by scenario oracles (output, state, trace, full scenario).

## Run

From repo root (requires `OPENAI_API_KEY` and dev dependency group):

```bash
OPENAI_API_KEY=... uv run agent-spec-kit run benchmarks/telecom_support/ --tags pilot,reference
```

Fault-detection matrix (F01–F10 mutation-style faults; **does not re-run or change the reference agent**):

```bash
# Eligibility from frozen baseline_T01_T50.log (one-time; committed as eligibility.json)
uv run python benchmarks/telecom_support/scripts/build_fault_eligibility.py

# Regenerate scenarios after editing manual tests
uv run python benchmarks/telecom_support/scripts/bootstrap_fault_detection.py

# Run primary matrix (live LLM) and parse log
TELCO_DISABLE_CALIBRATION_STEERING=1 OPENAI_API_KEY=... \
  uv run python benchmarks/telecom_support/scripts/run_fault_detection.py --run --workers 4

# Tables from real run JSON only
uv run python benchmarks/telecom_support/scripts/generate_fault_detection_table.py
```

Artifacts: [`tasks/fault_detection/`](tasks/fault_detection/) (`fault_matrix.yaml`, `eligibility.json`, `fault_detection_results.json`, generated `FAULT_DETECTION_TABLE.md`).

Legacy pilot (unsupported credit on `task_pilot_credit`):

```bash
OPENAI_API_KEY=... uv run agent-spec-kit run benchmarks/telecom_support/ --tags fault-detection
```

Parallel workers (safe: each job gets its own temp DB via fixtures):

```bash
OPENAI_API_KEY=... uv run agent-spec-kit run benchmarks/telecom_support/ -n 4 --tags pilot,reference
```

## Architecture

- **Coordinator** — authentication, dialogue, root tools, delegates to specialists
- **NetworkDiagnosticsSpecialist** — nested tools + `response_format=NetworkAssessment`
- **BillingPolicySpecialist** — nested tools + `response_format=BillingDecision`
- Traces use `subgraphs=True` so nested tool calls appear under `run_*_specialist` for `m.tool_call(..., children=[...])`

Root tools include `heartbeat_ping` for parallel sibling oracle demos (T06, T38).

## Design

| Layer | Enforces policy? |
|-------|------------------|
| `policy.md` | Defines P1–P10 + specialist rules |
| Agent prompt | Instructs coordinator and specialists |
| Tools | **No** — permissive simulator (mechanical validation only) |
| Task oracles | **Yes** — O/S/T/F projections (`assert_output`, `assert_that`, `assert_tool_calls`) |

Do not add business-policy gates to tools; violations are evaluation signal.

## Oracle notation (50-task catalog)

| Label | Meaning |
|-------|---------|
| O | Output-only — final reply |
| S | State — SQLite rows (tickets, credits, sim_orders, audit) |
| T | Trace — tool order, nested specialists, `m.object` on structured results |
| F | Full scenario — O + S + T + conversation constraints |

Task metadata: [`tasks/catalog.py`](tasks/catalog.py). Scenarios for T01–T50 are added incrementally.

## Layout

- `store/` — schema, `TelcoStore`, seeds, tool factories (coordinator / network / billing)
- `agents/` — `schemas.py`, coordinator graph, prompts, fault registry
- `seeds/` — per-task JSON world state
- `tasks/manual/` — pilot scenarios
- `tasks/catalog.py` — T01–T50 metadata stub
- `tasks/specs/oracles.py` — policy assertion helpers
- `regressions/` — placeholder for `--extract` output

## Pilot tasks

| Task | Policies | Oracle focus |
|------|----------|----------------|
| `task_pilot_auth` | P1, P7 | Trace: auth before profile |
| `task_pilot_outage` | P4 | Trace: outage check before diagnostic |
| `task_pilot_credit` | P2 | State: no credit when seed ineligible |

## Expressiveness comparison

Per-check-type authoring effort (agent_spec_kit vs pytest vs LangSmith / Pydantic Evals / Promptfoo / Braintrust) lives in [`../expressiveness/`](../expressiveness/). Telecom tasks **exemplify** those checks; LOC and table numbers come from the expressiveness harness, not from T01–T50 directly.

## Deferred

- Full T01–T50 scenario implementations, user simulation (~20 tasks), fuzz (~15 tasks), shrink/extract
- Reference calibration failures per task table
- `uv run agent-spec-kit run benchmarks/telecom_support/ --shrink --extract`
