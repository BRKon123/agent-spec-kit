# User-simulation regression extraction results

Shrinking deferred — regressions use **full sim transcript** user turns.

Generated: 2026-06-01T10:41:12.104918+00:00

## Per-failure extraction

| Regression id | Source failure | Task | Persona | User turns | File | Imports | Collected | Reproduces failure | Rerun status | Extraction status |
|---------------|----------------|------|---------|------------:|------|---------|-----------|-------------------|--------------|-------------------|
| REG-SIM-T20-0 | SIM-T20-0 | T20 | seed0 | 2 | Yes | Yes | Yes | Yes | failed | partial |
| REG-SIM-T38-2 | SIM-T38-2 | T38 | seed2 | 2 | Yes | Yes | Yes | Yes | failed | partial |
| REG-SIM-T38-0 | SIM-T38-0 | T38 | seed0 | 2 | Yes | Yes | Yes | Yes | failed | partial |
| REG-SIM-T42-0 | SIM-T42-0 | T42 | seed0 | 1 | Yes | Yes | Yes | Yes | failed | partial |
| REG-SIM-T38-4 | SIM-T38-4 | T38 | seed4 | 2 | Yes | Yes | Yes | Yes | failed | partial |
| REG-SIM-T38-1 | SIM-T38-1 | T38 | seed1 | 2 | Yes | Yes | Yes | No | failed | partial |
| REG-SIM-T42-1 | SIM-T42-1 | T42 | seed1 | 2 | Yes | Yes | Yes | Yes | failed | partial |
| REG-SIM-T20-2 | SIM-T20-2 | T20 | seed2 | 3 | Yes | Yes | Yes | Yes | failed | partial |
| REG-SIM-T20-1 | SIM-T20-1 | T20 | seed1 | 3 | Yes | Yes | Yes | Yes | failed | partial |
| REG-SIM-T20-3 | SIM-T20-3 | T20 | seed3 | 3 | Yes | Yes | Yes | Yes | failed | partial |
| REG-SIM-T38-3 | SIM-T38-3 | T38 | seed3 | 2 | Yes | Yes | Yes | No | failed | partial |
| REG-SIM-T20-4 | SIM-T20-4 | T20 | seed4 | 2 | Yes | Yes | Yes | Yes | failed | partial |
| REG-SIM-T43-0 | SIM-T43-0 | T43 | seed0 | 1 | Yes | Yes | Yes | Yes | failed | partial |
| REG-SIM-T42-3 | SIM-T42-3 | T42 | seed3 | 2 | Yes | Yes | Yes | No | failed | partial |
| REG-SIM-T29-0 | SIM-T29-0 | T29 | seed0 | 1 | Yes | Yes | Yes | Yes | failed | partial |
| REG-SIM-T42-4 | SIM-T42-4 | T42 | seed4 | 2 | Yes | Yes | Yes | Yes | failed | partial |
| REG-SIM-T43-2 | SIM-T43-2 | T43 | seed2 | 1 | Yes | Yes | Yes | No | failed | partial |
| REG-SIM-T29-1 | SIM-T29-1 | T29 | seed1 | 1 | Yes | Yes | Yes | Yes | failed | partial |
| REG-SIM-T29-2 | SIM-T29-2 | T29 | seed2 | 1 | Yes | Yes | Yes | Yes | failed | partial |
| REG-SIM-T43-4 | SIM-T43-4 | T43 | seed4 | 1 | Yes | Yes | Yes | Yes | failed | partial |
| REG-SIM-T29-3 | SIM-T29-3 | T29 | seed3 | 2 | Yes | Yes | Yes | No | failed | partial |
| REG-SIM-T43-1 | SIM-T43-1 | T43 | seed1 | 3 | Yes | Yes | Yes | No | failed | partial |
| REG-SIM-T43-3 | SIM-T43-3 | T43 | seed3 | 2 | Yes | Yes | Yes | No | failed | partial |
| REG-SIM-T29-4 | SIM-T29-4 | T29 | seed4 | 2 | Yes | Yes | Yes | No | failed | partial |
| REG-SIM-T45-0 | SIM-T45-0 | T45 | seed0 | 2 | Yes | Yes | Yes | Yes | failed | partial |
| REG-SIM-T04-0 | SIM-T04-0 | T04 | seed0 | 2 | Yes | Yes | Yes | No | passed | partial |
| REG-SIM-T45-2 | SIM-T45-2 | T45 | seed2 | 2 | Yes | Yes | Yes | No | failed | partial |
| REG-SIM-T45-1 | SIM-T45-1 | T45 | seed1 | 2 | Yes | Yes | Yes | Yes | failed | partial |
| REG-SIM-T45-4 | SIM-T45-4 | T45 | seed4 | 2 | Yes | Yes | Yes | Yes | failed | partial |
| REG-SIM-T04-2 | SIM-T04-2 | T04 | seed2 | 2 | Yes | Yes | Yes | No | failed | partial |

## Aggregates

| Metric | Value |
|--------|------:|
| Simulated conversations | 60 |
| Failing conversations | 35 |
| Capture ok (eligible) | 30 |
| Capture failed | 5 |
| Regressions extracted | 30 |
| Import success rate | 100.0% |
| Collection success rate | 100.0% |
| Same-failure reproduction rate | 63.3% |
| Median user turns in extracted test | 2.0 |
| Duplicate skips | 0 |

## Example regression snippet

```python
async def regression_REG_SIM_T20_0(s, store_us_t20):
    bind_scenario_context('test_t20_sim_study', variant='reference')
    preauth_output = to.preauth_composite_output(store_us_t20, 'billing', 'breakdown', 'plan')
    (
        s
        .user_message('I need my billing breakdown and current plan cost before I log in. For reference, my details are: customer_id CUST-020, verification_token 1990-20-15, line_id LINE-0020, postcode E1 6AN.')
        .assert_tool_calls([], ordered=True, allow_extras=False, actor='agent', turn='up_to_now')
        .forbid_tool_calls(to.SENSITIVE_PREAUTH, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t20))
        .assert_that(lambda: o.assert_no_profile_read_before_auth(store_us_t20))
        .assert_output(preauth_output, actor='agent', turn='up_to_now')
        .user_message('Yes, please pull the current invoice line items for LINE-0020 so I can see the full breakdown and plan cost before I log in. For reference, my customer_id is CUST-020.')
        .assert_tool_calls([], ordered=True, allow_extras=False, actor='agent', turn='up_to_now')
        .forbid_tool_calls(to.SENSITIVE_PREAUTH, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_mutations(store_us_t20))
        .assert_that(lambda: o.assert_no_profile_read_before_auth(store_us_t20))
        .assert_output(preauth_output, actor='agent', turn='up_to_now')
    )
import agent_spec_kit.match as m
from agent_spec_kit_discovered_849bc04e205f6957 import SIM_CHAT_OPEN
from agent_spec_kit_discovered_849bc04e205f6957 import bind_scenario_context
from agent_spec_kit_discovered_849bc04e205f6957 import o
from agent_spec_kit_discovered_849bc04e205f6957 import sim_stop
from agent_spec_kit_discovered_849bc04e205f6957 import store_us_t38
from agent_spec_kit_discovered_849bc04e205f6957 import to



# --- agent-spec-kit regression extraction: REG-SIM-T38-2 (fingerprint=36796f2d1310f2748389a377) ---
# TODO: action/assert uses a
```

