# LangChain nested tool-oracle example

Live example (`OPENAI_API_KEY` required) demonstrating **tool-call oracles** in one incident-triage story:

| Matcher knob | What the pass scenario exercises |
|--------------|----------------------------------|
| **Ordering** | `ordered=True`, `allow_extras=True` — policy subsequence on root tools |
| **Nested `children`** | `pull_logs` → `score_anomaly` under `run_forensics_specialist` |
| **Deep args** | `m.object` / `m.regex` / `m.list` on `open_incident`, `pull_logs`, `score_anomaly` |
| **Conditional args** | `m.require` / `m.forbid` / `m.field(...).when(...)` on `ticket` and flat `score_anomaly` fields |
| **Whole-object predicate** | `.where(...)` on `score_anomaly` args (`anomaly_score >= 0.5`) |
| **LLM rubrics** | `m.llm_criteria` on `score_anomaly.result` and `run_forensics_specialist.result` |

## Run

From the repo root:

```bash
OPENAI_API_KEY=... uv run agent-spec-kit run examples/langchain_nested_tool_oracle/
```

Pass scenario: `test_incident_triage_oracle` (tag `smoke`).

## Variants

**Unordered parallel siblings** (two-turn flow):

```bash
OPENAI_API_KEY=... uv run agent-spec-kit run examples/langchain_nested_tool_oracle/ --tags parallel-unordered
```

**Expected failures** (counterexample teaching — `conditional_rule`, nested order, etc.):

```bash
OPENAI_API_KEY=... uv run agent-spec-kit run examples/langchain_nested_tool_oracle/ --tags expected-failure
```

| Scenario | Intended failure signal |
|----------|-------------------------|
| `test_incident_wrong_nested_order` | Nested `children` ordering |
| `test_incident_missing_pager_on_high` | `conditional_rule` on `open_incident.args.ticket` |
| `test_incident_logs_without_window` | `conditional_rule` on `score_anomaly.args.window_minutes` |

Failure scenarios use `adapted_agent_failure_mode`, which follows adversarial user instructions instead of the strict runbook.

## Layout

- `fixtures.py` — coordinator + forensics specialist subgraph (`subgraphs=True`)
- `test_nested_tool_oracle.py` — scenarios with inlined matcher specs
