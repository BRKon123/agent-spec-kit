# Tool error message gallery

Deterministic **expected-failure** scenarios for eyeballing `assert_tool_calls` failure
boxes (Path / Expected / Actual). No LLM or API keys.

## Run

```bash
uv run agent-spec-kit run examples/tool_error_messages/
uv run agent-spec-kit run examples/tool_error_messages/ --tags fail-name-at-index-1
```

All scenarios are tagged `expected-failure` and `tool-error-demo`.

## Scenario index

| Scenario | Tag | Trigger | Expected path (typical) | Look for in Expected |
|----------|-----|---------|-------------------------|----------------------|
| `test_fail_name_at_index_0` | `fail-name-at-index-0` | `trace:auth-order` | `$[0].name` | `[1]` stubbed to name only; wrong tool at `[0]` |
| `test_fail_name_at_index_1` | `fail-name-at-index-1` | `trace:auth-order` | `$[1].name` | `[0]` name-only stub; `[1]` shows expected tool name |
| `test_fail_list_length` | `fail-list-length` | `trace:auth-only` | `$` | Tool count + optional spec preview |
| `test_fail_arg_value` | `fail-arg-value` | `trace:auth-order` | `$[1].args.line_id` | Focused `line_id` constraint; other args truncated |
| `test_fail_extra_arg` | `fail-extra-arg` | `trace:order-sim-type` | `$[0].args.sim_type` | Full expected `args` (extra key not in spec) |
| `test_fail_missing_arg` | `fail-missing-arg` | `trace:order-line-only` | `$[0].args.address_id` | Missing required arg visible in Expected |
| `test_fail_nested_child_name` | `fail-nested-child-name` | `trace:nested-forensics` | `$[0].children[1].name` | Nested children; wrong child name |
| `test_fail_nested_arg` | `fail-nested-arg` | `trace:nested-forensics` | `$[0].children[1].args.window_minutes` | Conditional require on nested args |
| `test_fail_large_spec_truncation` | `fail-large-spec-truncation` | `trace:five-tools` | `$[3].args.step` | Middle tools collapsed; focus tool expanded |
| `test_fail_forbidden_tool` | `fail-forbidden-tool` | `trace:with-credit` | `$[1]` | Forbidden tool pattern in Expected |

The agent returns fixed tool traces keyed by `trace:…` phrases in the user message (see `fixtures.py`).
