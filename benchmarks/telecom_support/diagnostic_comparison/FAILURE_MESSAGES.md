# Failure messages (diagnostic comparison)

Generated from `fault_detection_primary.log`. Scope: `detected_f`.

## F01|T44
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f01_t44_full [1/1] ────────────────────────╮
│ Check: assert_tool_calls                                                     │
│ Where: 1st assert_tool_calls after t`
- **pytest_plain**: `AssertionError: mismatch at $[0].name`
- **langsmith**: `{'key': 'tool_sequence', 'score': 0}`
- **pydantic_evals**: `AssertionError: mismatch at $[0].name`
- **promptfoo**: `assertion returned False`
- **braintrust**: `{'key': 'f01_tool_sequence', 'score': 0}`

## F02|T29
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f02_t29_full [1/1] ────────────────────────╮
│ Check: assert_tool_calls                                                     │
│ Where: 1st assert_tool_calls after t`
- **pytest_plain**: `AssertionError: mismatch at $[1].args.sim_type`
- **langsmith**: `{'key': 'tool_sequence', 'score': 0}`
- **pydantic_evals**: `AssertionError: mismatch at $[1].args.sim_type`
- **promptfoo**: `assertion returned False`
- **braintrust**: `{'key': 'f02_tool_sequence', 'score': 0}`

## F02|T43
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f02_t43_full [1/1] ────────────────────────╮
│ Check: assert_that                                                           │
│ Where: 1st assert_that after turn #6`
- **pytest_plain**: `expected no ticket on line 'LINE-0043B', found
1`
- **langsmith**: `{'key': 'state_oracle', 'score': 0}`
- **pydantic_evals**: `expected no ticket on line 'LINE-0043B', found
1`
- **promptfoo**: `assertion returned False`
- **braintrust**: `{'key': 'f02_state_oracle', 'score': 0}`

## F02|T46
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f02_t46_full [1/1] ────────────────────────╮
│ Check: assert_tool_calls                                                     │
│ Where: 1st assert_tool_calls after t`
- **pytest_plain**: `AssertionError: mismatch at $[1].args.step`
- **langsmith**: `{'key': 'tool_sequence', 'score': 0}`
- **pydantic_evals**: `AssertionError: mismatch at $[1].args.step`
- **promptfoo**: `assertion returned False`
- **braintrust**: `{'key': 'f02_tool_sequence', 'score': 0}`

## F03|T17
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f03_t17_full [1/1] ────────────────────────╮
│ Check: assert_that                                                           │
│ Where: 1st assert_that after turn #2`
- **pytest_plain**: `expected zero credits, found 2`
- **langsmith**: `{'key': 'state_oracle', 'score': 0}`
- **pydantic_evals**: `expected zero credits, found 2`
- **promptfoo**: `assertion returned False`
- **braintrust**: `{'key': 'f03_state_oracle', 'score': 0}`

## F03|T27
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f03_t27_full [1/1] ────────────────────────╮
│ Check: assert_that                                                           │
│ Where: 1st assert_that after turn #6`
- **pytest_plain**: `expected zero credits, found 2`
- **langsmith**: `{'key': 'state_oracle', 'score': 0}`
- **pydantic_evals**: `expected zero credits, found 2`
- **promptfoo**: `assertion returned False`
- **braintrust**: `{'key': 'f03_state_oracle', 'score': 0}`

## F04|T45
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f04_t45_full [1/1] ────────────────────────╮
│ Check: assert_that                                                           │
│ Where: 1st assert_that after turn #4`
- **pytest_plain**: `expected no
get_customer_profile/get_plan_details/get_line_status before auth`
- **langsmith**: `{'key': 'state_oracle', 'score': 0}`
- **pydantic_evals**: `expected no
get_customer_profile/get_plan_details/get_line_status before auth`
- **promptfoo**: `assertion returned False`
- **braintrust**: `{'key': 'f04_state_oracle', 'score': 0}`

## F04|T49
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f04_t49_full [1/1] ────────────────────────╮
│ Check: assert_that                                                           │
│ Where: 1st assert_that after turn #4`
- **pytest_plain**: `expected no
get_customer_profile/get_plan_details/get_line_status before auth`
- **langsmith**: `{'key': 'state_oracle', 'score': 0}`
- **pydantic_evals**: `expected no
get_customer_profile/get_plan_details/get_line_status before auth`
- **promptfoo**: `assertion returned False`
- **braintrust**: `{'key': 'f04_state_oracle', 'score': 0}`

## F04|T50
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f04_t50_full [1/1] ────────────────────────╮
│ Check: assert_output                                                         │
│ Where: 1st assert_output after turn `
- **pytest_plain**: `AssertionError`
- **langsmith**: `{'key': 'output_rubric', 'score': 0}`
- **pydantic_evals**: `AssertionError`
- **promptfoo**: `assertion returned False`
- **braintrust**: `{'key': 'f04_output_rubric', 'score': 0}`

## F05|T38
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f05_t38_full [1/1] ────────────────────────╮
│ Check: assert_tool_calls                                                     │
│ Where: 1st assert_tool_calls after t`
- **pytest_plain**: `AssertionError: mismatch at $[1].children`
- **langsmith**: `{'key': 'tool_sequence', 'score': 0}`
- **pydantic_evals**: `AssertionError: mismatch at $[1].children`
- **promptfoo**: `assertion returned False`
- **braintrust**: `{'key': 'f05_tool_sequence', 'score': 0}`

## F07|T29
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f07_t29_full [1/1] ────────────────────────╮
│ Check: forbid_tool_calls                                                     │
│ Where: 1st forbid_tool_calls after t`
- **pytest_plain**: `AssertionError: mismatch at $[0]`
- **langsmith**: `{'key': 'forbidden_tools', 'score': 0}`
- **pydantic_evals**: `AssertionError: mismatch at $[0]`
- **promptfoo**: `assertion returned False`
- **braintrust**: `{'key': 'f07_forbidden_tools', 'score': 0}`

## F07|T30
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f07_t30_full [1/1] ────────────────────────╮
│ Check: forbid_tool_calls                                                     │
│ Where: 1st forbid_tool_calls after t`
- **pytest_plain**: `AssertionError: mismatch at $[1]`
- **langsmith**: `{'key': 'forbidden_tools', 'score': 0}`
- **pydantic_evals**: `AssertionError: mismatch at $[1]`
- **promptfoo**: `assertion returned False`
- **braintrust**: `{'key': 'f07_forbidden_tools', 'score': 0}`

## F07|T42
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f07_t42_full [1/1] ────────────────────────╮
│ Check: forbid_tool_calls                                                     │
│ Where: 1st forbid_tool_calls after t`
- **pytest_plain**: `AssertionError: mismatch at $[1]`
- **langsmith**: `{'key': 'forbidden_tools', 'score': 0}`
- **pydantic_evals**: `AssertionError: mismatch at $[1]`
- **promptfoo**: `assertion returned False`
- **braintrust**: `{'key': 'f07_forbidden_tools', 'score': 0}`

## F07|T43
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f07_t43_full [1/1] ────────────────────────╮
│ Check: forbid_tool_calls                                                     │
│ Where: 1st forbid_tool_calls after t`
- **pytest_plain**: `AssertionError: mismatch at $[0]`
- **langsmith**: `{'key': 'forbidden_tools', 'score': 0}`
- **pydantic_evals**: `AssertionError: mismatch at $[0]`
- **promptfoo**: `assertion returned False`
- **braintrust**: `{'key': 'f07_forbidden_tools', 'score': 0}`

## F08|T21
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f08_t21_full [1/1] ────────────────────────╮
│ Check: assert_that                                                           │
│ Where: 2nd assert_that after turn #2`
- **pytest_plain**: `expected at least one audit note`
- **langsmith**: `{'key': 'state_oracle', 'score': 0}`
- **pydantic_evals**: `expected at least one audit note`
- **promptfoo**: `assertion returned False`
- **braintrust**: `{'key': 'f08_state_oracle', 'score': 0}`

## F09|T04
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f09_t04_full [1/1] ────────────────────────╮
│ Check: assert_that                                                           │
│ Where: 1st assert_that after turn #4`
- **pytest_plain**: `expected at least one ticket`
- **langsmith**: `{'key': 'state_oracle', 'score': 0}`
- **pydantic_evals**: `expected at least one ticket`
- **promptfoo**: `assertion returned False`
- **braintrust**: `{'key': 'f09_state_oracle', 'score': 0}`

## F09|T19
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f09_t19_full [1/1] ────────────────────────╮
│ Check: assert_that                                                           │
│ Where: 2nd assert_that after turn #2`
- **pytest_plain**: `expected at least one ticket`
- **langsmith**: `{'key': 'state_oracle', 'score': 0}`
- **pydantic_evals**: `expected at least one ticket`
- **promptfoo**: `assertion returned False`
- **braintrust**: `{'key': 'f09_state_oracle', 'score': 0}`

## F10|T29
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f10_t29_full [1/1] ────────────────────────╮
│ Check: assert_tool_calls                                                     │
│ Where: 1st assert_tool_calls after t`
- **pytest_plain**: `AssertionError: mismatch at $[1].args.sim_type`
- **langsmith**: `{'key': 'tool_sequence', 'score': 0}`
- **pydantic_evals**: `AssertionError: mismatch at $[1].args.sim_type`
- **promptfoo**: `assertion returned False`
- **braintrust**: `{'key': 'f10_tool_sequence', 'score': 0}`

## F10|T42
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f10_t42_full [1/1] ────────────────────────╮
│ Check: assert_that                                                           │
│ Where: 1st assert_that after turn #4`
- **pytest_plain**: `expected zero tickets, found 1`
- **langsmith**: `{'key': 'state_oracle', 'score': 0}`
- **pydantic_evals**: `expected zero tickets, found 1`
- **promptfoo**: `assertion returned False`
- **braintrust**: `{'key': 'f10_state_oracle', 'score': 0}`

## F10|T43
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f10_t43_full [1/1] ────────────────────────╮
│ Check: assert_output                                                         │
│ Where: 1st assert_output after turn `
- **pytest_plain**: `AssertionError`
- **langsmith**: `{'key': 'output_rubric', 'score': 0}`
- **pydantic_evals**: `AssertionError`
- **promptfoo**: `assertion returned False`
- **braintrust**: `{'key': 'f10_output_rubric', 'score': 0}`

## F10|T44
- **agent_spec_kit**: `╭──────────────────────── FAIL test_f10_t44_full [1/1] ────────────────────────╮
│ Check: assert_tool_calls                                                     │
│ Where: 1st assert_tool_calls after t`
- **pytest_plain**: `AssertionError: mismatch at $[0].name`
- **langsmith**: `{'key': 'tool_sequence', 'score': 0}`
- **pydantic_evals**: `AssertionError: mismatch at $[0].name`
- **promptfoo**: `assertion returned False`
- **braintrust**: `{'key': 'f10_tool_sequence', 'score': 0}`

