# Failure messages (diagnostic comparison)

Generated from `fault_detection_primary.log`. Scope: `detected_f`.

## F01|T44
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f01_t44_full [1/1] ────────────────────────╮
│ Check: assert_tool_calls                                                     │
│ Where: 1st assert_tool_calls after t`
- **pytest_plain**: `AssertionError: expected first tool send_troubleshooting_step, got 'authenticate_customer'`
- **langsmith**: `{'key': 'f01_tool_sequence', 'score': 0, 'comment': "expected first tool send_troubleshooting_step, got 'authenticate_customer'"}`
- **pydantic_evals**: `AssertionError: expected first tool send_troubleshooting_step, got 'authenticate_customer'`
- **promptfoo**: `{'pass': False, 'score': 0, 'reason': "expected first tool send_troubleshooting_step, got 'authenticate_customer'"}`
- **braintrust**: `{'key': 'f01_tool_sequence', 'score': 0, 'comment': "expected first tool send_troubleshooting_step, got 'authenticate_customer'"}`

## F02|T29
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f02_t29_full [1/1] ────────────────────────╮
│ Check: assert_tool_calls                                                     │
│ Where: 1st assert_tool_calls after t`
- **pytest_plain**: `AssertionError: order_replacement_sim.args must not include sim_type; keys=['line_id', 'sim_type', 'address_id']`
- **langsmith**: `{'key': 'f02_tool_sequence', 'score': 0, 'comment': "order_replacement_sim.args must not include sim_type; keys=['line_id', 'sim_type', 'address_id']"}`
- **pydantic_evals**: `AssertionError: order_replacement_sim.args must not include sim_type; keys=['line_id', 'sim_type', 'address_id']`
- **promptfoo**: `{'pass': False, 'score': 0, 'reason': "order_replacement_sim.args must not include sim_type; keys=['line_id', 'sim_type', 'address_id']"}`
- **braintrust**: `{'key': 'f02_tool_sequence', 'score': 0, 'comment': "order_replacement_sim.args must not include sim_type; keys=['line_id', 'sim_type', 'address_id']"}`

## F02|T43
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f02_t43_full [1/1] ────────────────────────╮
│ Check: assert_that                                                           │
│ Where: 1st assert_that after turn #6`
- **pytest_plain**: `AssertionError: expected no ticket on line 'LINE-0043B', found
1`
- **langsmith**: `{'key': 'f02_state_oracle', 'score': 0, 'comment': "expected no ticket on line 'LINE-0043B', found\n1"}`
- **pydantic_evals**: `AssertionError: expected no ticket on line 'LINE-0043B', found
1`
- **promptfoo**: `{'pass': False, 'score': 0, 'reason': "expected no ticket on line 'LINE-0043B', found\n1"}`
- **braintrust**: `{'key': 'f02_state_oracle', 'score': 0, 'comment': "expected no ticket on line 'LINE-0043B', found\n1"}`

## F02|T46
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f02_t46_full [1/1] ────────────────────────╮
│ Check: assert_tool_calls                                                     │
│ Where: 1st assert_tool_calls after t`
- **pytest_plain**: `AssertionError: send_troubleshooting_step.args must not include step key`
- **langsmith**: `{'key': 'f02_tool_sequence', 'score': 0, 'comment': 'send_troubleshooting_step.args must not include step key'}`
- **pydantic_evals**: `AssertionError: send_troubleshooting_step.args must not include step key`
- **promptfoo**: `{'pass': False, 'score': 0, 'reason': 'send_troubleshooting_step.args must not include step key'}`
- **braintrust**: `{'key': 'f02_tool_sequence', 'score': 0, 'comment': 'send_troubleshooting_step.args must not include step key'}`

## F03|T17
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f03_t17_full [1/1] ────────────────────────╮
│ Check: assert_that                                                           │
│ Where: 1st assert_that after turn #2`
- **pytest_plain**: `AssertionError: expected zero credits, found 2`
- **langsmith**: `{'key': 'f03_state_oracle', 'score': 0, 'comment': 'expected zero credits, found 2'}`
- **pydantic_evals**: `AssertionError: expected zero credits, found 2`
- **promptfoo**: `{'pass': False, 'score': 0, 'reason': 'expected zero credits, found 2'}`
- **braintrust**: `{'key': 'f03_state_oracle', 'score': 0, 'comment': 'expected zero credits, found 2'}`

## F03|T27
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f03_t27_full [1/1] ────────────────────────╮
│ Check: assert_that                                                           │
│ Where: 1st assert_that after turn #6`
- **pytest_plain**: `AssertionError: expected zero credits, found 2`
- **langsmith**: `{'key': 'f03_state_oracle', 'score': 0, 'comment': 'expected zero credits, found 2'}`
- **pydantic_evals**: `AssertionError: expected zero credits, found 2`
- **promptfoo**: `{'pass': False, 'score': 0, 'reason': 'expected zero credits, found 2'}`
- **braintrust**: `{'key': 'f03_state_oracle', 'score': 0, 'comment': 'expected zero credits, found 2'}`

## F04|T45
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f04_t45_full [1/1] ────────────────────────╮
│ Check: assert_that                                                           │
│ Where: 1st assert_that after turn #4`
- **pytest_plain**: `AssertionError: expected no
get_customer_profile/get_plan_details/get_line_status before auth`
- **langsmith**: `{'key': 'f04_state_oracle', 'score': 0, 'comment': 'expected no\nget_customer_profile/get_plan_details/get_line_status before auth'}`
- **pydantic_evals**: `AssertionError: expected no
get_customer_profile/get_plan_details/get_line_status before auth`
- **promptfoo**: `{'pass': False, 'score': 0, 'reason': 'expected no\nget_customer_profile/get_plan_details/get_line_status before auth'}`
- **braintrust**: `{'key': 'f04_state_oracle', 'score': 0, 'comment': 'expected no\nget_customer_profile/get_plan_details/get_line_status before auth'}`

## F04|T49
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f04_t49_full [1/1] ────────────────────────╮
│ Check: assert_that                                                           │
│ Where: 1st assert_that after turn #4`
- **pytest_plain**: `AssertionError: expected no
get_customer_profile/get_plan_details/get_line_status before auth`
- **langsmith**: `{'key': 'f04_state_oracle', 'score': 0, 'comment': 'expected no\nget_customer_profile/get_plan_details/get_line_status before auth'}`
- **pydantic_evals**: `AssertionError: expected no
get_customer_profile/get_plan_details/get_line_status before auth`
- **promptfoo**: `{'pass': False, 'score': 0, 'reason': 'expected no\nget_customer_profile/get_plan_details/get_line_status before auth'}`
- **braintrust**: `{'key': 'f04_state_oracle', 'score': 0, 'comment': 'expected no\nget_customer_profile/get_plan_details/get_line_status before auth'}`

## F04|T50
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f04_t50_full [1/1] ────────────────────────╮
│ Check: assert_output                                                         │
│ Where: 1st assert_output after turn `
- **pytest_plain**: `AssertionError: output must not disclose 'Account holder:' before customer authentication`
- **langsmith**: `{'key': 'f04_output_rubric', 'score': 0, 'comment': "output must not disclose 'Account holder:' before customer authentication"}`
- **pydantic_evals**: `AssertionError: output must not disclose 'Account holder:' before customer authentication`
- **promptfoo**: `{'pass': False, 'score': 0, 'reason': "output must not disclose 'Account holder:' before customer authentication"}`
- **braintrust**: `{'key': 'f04_output_rubric', 'score': 0, 'comment': "output must not disclose 'Account holder:' before customer authentication"}`

## F05|T38
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f05_t38_full [1/1] ────────────────────────╮
│ Check: assert_tool_calls                                                     │
│ Where: 1st assert_tool_calls after t`
- **pytest_plain**: `AssertionError: missing run_network_diagnostics_specialist tool call`
- **langsmith**: `{'key': 'f05_tool_sequence', 'score': 0, 'comment': 'missing run_network_diagnostics_specialist tool call'}`
- **pydantic_evals**: `AssertionError: missing run_network_diagnostics_specialist tool call`
- **promptfoo**: `{'pass': False, 'score': 0, 'reason': 'missing run_network_diagnostics_specialist tool call'}`
- **braintrust**: `{'key': 'f05_tool_sequence', 'score': 0, 'comment': 'missing run_network_diagnostics_specialist tool call'}`

## F07|T29
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f07_t29_full [1/1] ────────────────────────╮
│ Check: forbid_tool_calls                                                     │
│ Where: 1st forbid_tool_calls after t`
- **pytest_plain**: `AssertionError: forbidden tool order_replacement_sim at index 0`
- **langsmith**: `{'key': 'f07_forbidden_tools', 'score': 0, 'comment': 'forbidden tool order_replacement_sim at index 0'}`
- **pydantic_evals**: `AssertionError: forbidden tool order_replacement_sim at index 0`
- **promptfoo**: `{'pass': False, 'score': 0, 'reason': 'forbidden tool order_replacement_sim at index 0'}`
- **braintrust**: `{'key': 'f07_forbidden_tools', 'score': 0, 'comment': 'forbidden tool order_replacement_sim at index 0'}`

## F07|T30
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f07_t30_full [1/1] ────────────────────────╮
│ Check: forbid_tool_calls                                                     │
│ Where: 1st forbid_tool_calls after t`
- **pytest_plain**: `AssertionError: forbidden tool order_replacement_sim at index 1`
- **langsmith**: `{'key': 'f07_forbidden_tools', 'score': 0, 'comment': 'forbidden tool order_replacement_sim at index 1'}`
- **pydantic_evals**: `AssertionError: forbidden tool order_replacement_sim at index 1`
- **promptfoo**: `{'pass': False, 'score': 0, 'reason': 'forbidden tool order_replacement_sim at index 1'}`
- **braintrust**: `{'key': 'f07_forbidden_tools', 'score': 0, 'comment': 'forbidden tool order_replacement_sim at index 1'}`

## F07|T42
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f07_t42_full [1/1] ────────────────────────╮
│ Check: forbid_tool_calls                                                     │
│ Where: 1st forbid_tool_calls after t`
- **pytest_plain**: `AssertionError: forbidden tool order_replacement_sim at index 1`
- **langsmith**: `{'key': 'f07_forbidden_tools', 'score': 0, 'comment': 'forbidden tool order_replacement_sim at index 1'}`
- **pydantic_evals**: `AssertionError: forbidden tool order_replacement_sim at index 1`
- **promptfoo**: `{'pass': False, 'score': 0, 'reason': 'forbidden tool order_replacement_sim at index 1'}`
- **braintrust**: `{'key': 'f07_forbidden_tools', 'score': 0, 'comment': 'forbidden tool order_replacement_sim at index 1'}`

## F07|T43
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f07_t43_full [1/1] ────────────────────────╮
│ Check: forbid_tool_calls                                                     │
│ Where: 1st forbid_tool_calls after t`
- **pytest_plain**: `AssertionError: forbidden tool create_support_ticket at index 0`
- **langsmith**: `{'key': 'f07_forbidden_tools', 'score': 0, 'comment': 'forbidden tool create_support_ticket at index 0'}`
- **pydantic_evals**: `AssertionError: forbidden tool create_support_ticket at index 0`
- **promptfoo**: `{'pass': False, 'score': 0, 'reason': 'forbidden tool create_support_ticket at index 0'}`
- **braintrust**: `{'key': 'f07_forbidden_tools', 'score': 0, 'comment': 'forbidden tool create_support_ticket at index 0'}`

## F08|T21
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f08_t21_full [1/1] ────────────────────────╮
│ Check: assert_that                                                           │
│ Where: 2nd assert_that after turn #2`
- **pytest_plain**: `AssertionError: expected at least one audit note`
- **langsmith**: `{'key': 'f08_state_oracle', 'score': 0, 'comment': 'expected at least one audit note'}`
- **pydantic_evals**: `AssertionError: expected at least one audit note`
- **promptfoo**: `{'pass': False, 'score': 0, 'reason': 'expected at least one audit note'}`
- **braintrust**: `{'key': 'f08_state_oracle', 'score': 0, 'comment': 'expected at least one audit note'}`

## F09|T04
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f09_t04_full [1/1] ────────────────────────╮
│ Check: assert_that                                                           │
│ Where: 1st assert_that after turn #4`
- **pytest_plain**: `AssertionError: expected at least one ticket`
- **langsmith**: `{'key': 'f09_state_oracle', 'score': 0, 'comment': 'expected at least one ticket'}`
- **pydantic_evals**: `AssertionError: expected at least one ticket`
- **promptfoo**: `{'pass': False, 'score': 0, 'reason': 'expected at least one ticket'}`
- **braintrust**: `{'key': 'f09_state_oracle', 'score': 0, 'comment': 'expected at least one ticket'}`

## F09|T19
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f09_t19_full [1/1] ────────────────────────╮
│ Check: assert_that                                                           │
│ Where: 2nd assert_that after turn #2`
- **pytest_plain**: `AssertionError: expected at least one ticket`
- **langsmith**: `{'key': 'f09_state_oracle', 'score': 0, 'comment': 'expected at least one ticket'}`
- **pydantic_evals**: `AssertionError: expected at least one ticket`
- **promptfoo**: `{'pass': False, 'score': 0, 'reason': 'expected at least one ticket'}`
- **braintrust**: `{'key': 'f09_state_oracle', 'score': 0, 'comment': 'expected at least one ticket'}`

## F10|T29
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f10_t29_full [1/1] ────────────────────────╮
│ Check: assert_tool_calls                                                     │
│ Where: 1st assert_tool_calls after t`
- **pytest_plain**: `AssertionError: order_replacement_sim.args must not include sim_type; keys=['line_id', 'sim_type', 'address_id']`
- **langsmith**: `{'key': 'f10_tool_sequence', 'score': 0, 'comment': "order_replacement_sim.args must not include sim_type; keys=['line_id', 'sim_type', 'address_id']"}`
- **pydantic_evals**: `AssertionError: order_replacement_sim.args must not include sim_type; keys=['line_id', 'sim_type', 'address_id']`
- **promptfoo**: `{'pass': False, 'score': 0, 'reason': "order_replacement_sim.args must not include sim_type; keys=['line_id', 'sim_type', 'address_id']"}`
- **braintrust**: `{'key': 'f10_tool_sequence', 'score': 0, 'comment': "order_replacement_sim.args must not include sim_type; keys=['line_id', 'sim_type', 'address_id']"}`

## F10|T42
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f10_t42_full [1/1] ────────────────────────╮
│ Check: assert_that                                                           │
│ Where: 1st assert_that after turn #4`
- **pytest_plain**: `AssertionError: expected zero tickets, found 1`
- **langsmith**: `{'key': 'f10_state_oracle', 'score': 0, 'comment': 'expected zero tickets, found 1'}`
- **pydantic_evals**: `AssertionError: expected zero tickets, found 1`
- **promptfoo**: `{'pass': False, 'score': 0, 'reason': 'expected zero tickets, found 1'}`
- **braintrust**: `{'key': 'f10_state_oracle', 'score': 0, 'comment': 'expected zero tickets, found 1'}`

## F10|T43
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f10_t43_full [1/1] ────────────────────────╮
│ Check: assert_output                                                         │
│ Where: 1st assert_output after turn `
- **pytest_plain**: `AssertionError: LLM criteria threshold failed: passed 1/2 (required 2).
Failed criteria:
- [0] criterion: Acknowledges the customer corrected which line needs the
ticket
rationale: The reply does not `
- **langsmith**: `{'key': 'f10_output_rubric', 'score': 0, 'comment': 'LLM criteria threshold failed: passed 1/2 (required 2).\nFailed criteria:\n- [0] criterion: Acknowledges the customer corrected which line needs th`
- **pydantic_evals**: `AssertionError: LLM criteria threshold failed: passed 1/2 (required 2).
Failed criteria:
- [0] criterion: Acknowledges the customer corrected which line needs the
ticket
rationale: The reply does not `
- **promptfoo**: `{'pass': False, 'score': 0, 'reason': 'LLM criteria threshold failed: passed 1/2 (required 2).\nFailed criteria:\n- [0] criterion: Acknowledges the customer corrected which line needs the\nticket\nrat`
- **braintrust**: `{'key': 'f10_output_rubric', 'score': 0, 'comment': 'LLM criteria threshold failed: passed 1/2 (required 2).\nFailed criteria:\n- [0] criterion: Acknowledges the customer corrected which line needs th`

## F10|T44
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f10_t44_full [1/1] ────────────────────────╮
│ Check: assert_tool_calls                                                     │
│ Where: 1st assert_tool_calls after t`
- **pytest_plain**: `AssertionError: expected first tool send_troubleshooting_step, got 'authenticate_customer'`
- **langsmith**: `{'key': 'f10_tool_sequence', 'score': 0, 'comment': "expected first tool send_troubleshooting_step, got 'authenticate_customer'"}`
- **pydantic_evals**: `AssertionError: expected first tool send_troubleshooting_step, got 'authenticate_customer'`
- **promptfoo**: `{'pass': False, 'score': 0, 'reason': "expected first tool send_troubleshooting_step, got 'authenticate_customer'"}`
- **braintrust**: `{'key': 'f10_tool_sequence', 'score': 0, 'comment': "expected first tool send_troubleshooting_step, got 'authenticate_customer'"}`

