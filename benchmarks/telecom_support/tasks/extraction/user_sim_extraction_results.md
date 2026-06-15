# User-simulation regression extraction results

Shrinking deferred — regressions use **full sim transcript** user turns.

Generated: 2026-06-03T13:07:32.460486+00:00

## Per-failure extraction

| Regression id | Source failure | Task | Persona | User turns | File | Imports | Collected | Reproduces failure | Rerun status | Extraction status |
|---------------|----------------|------|---------|------------:|------|---------|-----------|-------------------|--------------|-------------------|
| REG-SIM-T29-1 | SIM-T29-1 | T29 | seed1 | 1 | Yes | Yes | Yes | Yes | failed | skipped_duplicate |
| REG-SIM-T29-0 | SIM-T29-0 | T29 | seed0 | 1 | Yes | Yes | Yes | Yes | failed | skipped_duplicate |
| REG-SIM-T29-2 | SIM-T29-2 | T29 | seed2 | 1 | Yes | Yes | Yes | Yes | failed | skipped_duplicate |
| REG-SIM-T43-2 | SIM-T43-2 | T43 | seed2 | 1 | Yes | Yes | Yes | No | failed | skipped_duplicate |
| REG-SIM-T29-3 | SIM-T29-3 | T29 | seed3 | 1 | Yes | Yes | Yes | No | failed | skipped_duplicate |
| REG-SIM-T29-4 | SIM-T29-4 | T29 | seed4 | 1 | Yes | Yes | Yes | Yes | failed | skipped_duplicate |
| REG-SIM-T43-3 | SIM-T43-3 | T43 | seed3 | 3 | Yes | Yes | Yes | No | failed | skipped_duplicate |
| REG-SIM-T43-1 | SIM-T43-1 | T43 | seed1 | 3 | Yes | Yes | Yes | No | failed | skipped_duplicate |
| REG-SIM-T43-4 | SIM-T43-4 | T43 | seed4 | 3 | Yes | Yes | Yes | Yes | failed | skipped_duplicate |
| REG-SIM-T43-0 | SIM-T43-0 | T43 | seed0 | 3 | Yes | Yes | Yes | No | failed | skipped_duplicate |
| REG-SIM-T45-2 | SIM-T45-2 | T45 | seed2 | 3 | Yes | Yes | Yes | No | failed | skipped_duplicate |
| REG-SIM-T45-3 | SIM-T45-3 | T45 | seed3 | 2 | Yes | Yes | Yes | Yes | failed | partial |
| REG-SIM-T04-0 | SIM-T04-0 | T04 | seed0 | 2 | Yes | Yes | Yes | No | passed | skipped_duplicate |
| REG-SIM-T45-4 | SIM-T45-4 | T45 | seed4 | 2 | Yes | Yes | Yes | Yes | failed | skipped_duplicate |
| REG-SIM-T04-2 | SIM-T04-2 | T04 | seed2 | 2 | Yes | Yes | Yes | No | failed | skipped_duplicate |
| REG-SIM-T04-1 | SIM-T04-1 | T04 | seed1 | 3 | Yes | Yes | Yes | No | passed | partial |
| REG-SIM-T04-4 | SIM-T04-4 | T04 | seed4 | 2 | Yes | Yes | Yes | No | passed | partial |
| REG-SIM-T38-1 | SIM-T38-1 | T38 | seed1 | 2 | Yes | Yes | Yes | No | failed | skipped_duplicate |
| REG-SIM-T38-0 | SIM-T38-0 | T38 | seed0 | 2 | Yes | Yes | Yes | No | failed | skipped_duplicate |
| REG-SIM-T04-3 | SIM-T04-3 | T04 | seed3 | 4 | Yes | Yes | Yes | No | failed | partial |
| REG-SIM-T38-2 | SIM-T38-2 | T38 | seed2 | 5 | Yes | Yes | Yes | Yes | failed | skipped_duplicate |
| REG-SIM-T38-3 | SIM-T38-3 | T38 | seed3 | 2 | Yes | Yes | Yes | No | failed | skipped_duplicate |
| REG-SIM-T20-0 | SIM-T20-0 | T20 | seed0 | 2 | Yes | Yes | Yes | Yes | failed | skipped_duplicate |
| REG-SIM-T38-4 | SIM-T38-4 | T38 | seed4 | 2 | Yes | Yes | Yes | No | failed | skipped_duplicate |
| REG-SIM-T20-2 | SIM-T20-2 | T20 | seed2 | 3 | Yes | Yes | Yes | Yes | failed | skipped_duplicate |
| REG-SIM-T20-1 | SIM-T20-1 | T20 | seed1 | 3 | Yes | Yes | Yes | Yes | failed | skipped_duplicate |
| REG-SIM-T20-4 | SIM-T20-4 | T20 | seed4 | 2 | Yes | Yes | Yes | Yes | failed | skipped_duplicate |
| REG-SIM-T20-3 | SIM-T20-3 | T20 | seed3 | 3 | Yes | Yes | Yes | Yes | failed | skipped_duplicate |

## Aggregates

| Metric | Value |
|--------|------:|
| Simulated conversations | 60 |
| Failing conversations | 29 |
| Capture ok (eligible) | 28 |
| Capture failed | 1 |
| Regressions extracted | 28 |
| Import success rate | 100.0% |
| Collection success rate | 100.0% |
| Same-failure reproduction rate | 46.4% |
| Median user turns in extracted test | 2.0 |
| Duplicate skips | 24 |

## Example regression snippet

```python
async def regression_REG_SIM_T29_1(s, store_us_t29):
    bind_scenario_context('test_t29_sim_study', variant='reference')
    decoy = to.decoy_line_id(store_us_t29)
    seed_line = str(store_us_t29.seed_meta['line_id'])
    (
        s
        .user_message('Hi, I’m customer CUST-029 with verification token 1990-29-15. The line I need fixed is LINE-0029 (not LINE-WRONG); I need a replacement SIM sent to my default address at E1 6AN.')
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_sim_order_on_line(store_us_t29, decoy))
        .assert_output(to.clarification_output('Does not confirm a SIM order was placed on the wrong line', 'Asks which line is correct or acknowledges line uncertainty'), actor='agent', turn='up_to_now')
        .assert_tool_calls([m.tool_call('authenticate_customer'), to.order_sim_on_line(seed_line)], ordered=True, allow_extras=True, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_sim_orders_only_on_seed_line(store_us_t29))
        .assert_output(to.premature_action_output('LINE-WRONG', action='order'), actor='agent', turn='up_to_now')
    )

from agent_spec_kit_discovered_ad839d1428119abc import SIM_CHAT_OPEN
from agent_spec_kit_discovered_ad839d1428119abc import bind_scenario_context
from agent_spec_kit_discovered_ad839d1428119abc import o
from agent_spec_kit_discovered_ad839d1428119abc import sim_stop
from agent_spec_kit_discovered_ad839d1428119abc import store_us_t29
from agent_spec_kit_discovered_ad839d1428119abc import to



# --- agent-spec-kit regression extraction: REG-SIM-T29-2 (fingerprint=93adba08034b182135fa5c6e) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T29-2', tags=('telecom', 'regression', 'user-sim', 'extracted-sim'), agent_fixture='task_agent_us_t29', user_fixture='user_simulator_us_t29')
async def regression_REG_SIM_T29_2(s, store_us_t29):
    bind_scen
```

