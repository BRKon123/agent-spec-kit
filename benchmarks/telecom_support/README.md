# TelcoSupportBench-Lite

Miniature mobile-network customer-support benchmark for **agent-spec-kit**: permissive SQLite tools, policy in [`policy.md`](policy.md) and the agent prompt, compliance judged by scenario oracles (trace, state, output).

## Run

From repo root (requires `OPENAI_API_KEY` and dev dependency group):

```bash
OPENAI_API_KEY=... uv run agent-spec-kit run benchmarks/telecom_support/ --tags pilot,reference
```

Fault-detection pilot (P2 oracle should fail when fault agent applies credit):

```bash
OPENAI_API_KEY=... uv run agent-spec-kit run benchmarks/telecom_support/ --tags fault-detection
```

Parallel workers (safe: each job gets its own temp DB via fixtures):

```bash
OPENAI_API_KEY=... uv run agent-spec-kit run benchmarks/telecom_support/ -n 4 --tags pilot,reference
```

## Design

| Layer | Enforces policy? |
|-------|------------------|
| `policy.md` | Defines P1–P10 |
| Agent prompt | Instructs reference agent to follow policy |
| Tools | **No** — permissive simulator (mechanical validation only) |
| Task oracles | **Yes** — `assert_tool_calls`, `assert_that`, `assert_output` |

Do not add business-policy gates to tools; violations are evaluation signal.

## Layout

- `store/` — schema, `TelcoStore`, seeds loader, 15 tools
- `agents/` — reference graph + fault prompt variants / tool wrappers
- `seeds/` — per-task JSON world state
- `tasks/manual/` — pilot scenarios
- `tasks/specs/oracles.py` — policy assertion helpers
- `regressions/` — placeholder for `--extract` output

## Pilot tasks

| Task | Policies | Oracle focus |
|------|----------|----------------|
| `task_pilot_auth` | P1, P7 | Trace: auth before profile |
| `task_pilot_outage` | P4 | Trace: outage check before diagnostic |
| `task_pilot_credit` | P2 | State: no credit when seed ineligible |

## Deferred

- Full 30-task catalog, YAML spec loader, fuzz configs, user simulators (see plan Phase 2–3)
- Shrink/extract regressions: `uv run agent-spec-kit run benchmarks/telecom_support/ --shrink --extract`
