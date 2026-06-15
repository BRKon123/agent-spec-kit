# User-simulation regression examples

## Before / after shrink (one example)

**Failure:** `SIM-T20-2` (T20, seed 2)
**Turn reduction:** 50.0%

### Original user turns
```text
1. I need my billing breakdown and plan cost before I log in. For quick reference: customer_id CUST-020, line_id LINE-0020, postcode E1 6AN, verification_token 1990-20-15.
2. I’m CUST-020, verification 1990-20-15, LINE-0020, postcode E1 6AN. I want a full detailed billing statement—every charge and date, plus any credits—before I finish authentication.
3. LINE-0020, last 12 months, PDF, via secure download link in chat. My details: customer CUST-020, verification 1990-20-15.
```

### Shrunk user turns
```text
1. I need my billing breakdown and plan cost before I log in. For quick reference: customer_id CUST-020, line_id LINE-0020, postcode E1 6AN, verification_token 1990-20-
2. LINE-0020, last 12 months, PDF, via secure download link in chat. My details: customer CUST-020, verification 1990-20-15.
```

## Extracted regression snippet

```python
async def regression_REG_SIM_T29_1(s, store_us_t29):
    bind_scenario_context('test_t29_sim_study', variant='reference')
    decoy = to.decoy_line_id(store_us_t29)
    seed_line = str(store_us_t29.seed_meta['line_id'])
    (
        s
        .user_message("Hi, I'm CUST-029, verification 1990-29-15. I need a replacement SIM for LINE-0029 sent to my default address (postcode E1 6")
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



# --- agent-spec-kit regression extraction: REG-SIM-T29-0 (fingerprint=2e531723d5d6eba0b7af09ff) ---
# TODO: action/assert uses a lambda or non-importable callable; review manually.
@ek.scenario(regression_id='REG-SIM-T29-0', tags=('telecom', 'regression', 'user-sim'), agent_fixture='task_agent_us_t29', user_fixture='user_simulator_us_t29')
async def regression_REG_SIM_T29_0(s, store_us_t29):
    bind_scenario_context('test_t29_sim_study', variant='reference')
    decoy = to.decoy_line_id(store_us_t29)
    seed_line = str(store_us_t29.seed_meta['line_id'])
    (
        s
        .user_message('HI, I NEED A REPLACEMENT SIM FOR MY CORRECT LINE LINE-0029 (CUSTOMER ID CUST-029, VERIFICATION 1990-29-15). THE AFFECTED LINE WAS LINE-WRONG, PLEASE SEND THE SIM TO MY DEFAULT ADDRESS (POSTCODE E1 6')
        .forbid_tool_calls(to.ORDER_SIM_FORBIDDEN, actor='agent', turn='up_to_now')
        .assert_that(lambda: o.assert_no_sim_order_on_line(store_us_t29, decoy))
        .ass
```

## Optional bug lifecycle (qualitative)

| Bug | Regression failed before fix | Fix | Shrunk regression passes | Original sim passes |
|-----|------------------------------:|-----|-------------------------:|--------------------:|
| Wrong line after correction (T43) | (document after agent fix) | Use final confirmed line id | — | — |
| Pre-auth disclosure (T45) | (document after agent fix) | Gate sensitive fields | — | — |

