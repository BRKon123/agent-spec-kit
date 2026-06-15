# Manual inspection burden review


## F01/T44

### ask
- check: assert_tool_calls
- path: `$[0].name`
- expected snippet: equality: expected 'send_troubleshooting_step'

### ask
```
╭──────────────────────── FAIL test_f01_t44_full [1/1] ────────────────────────╮
│ Check: assert_tool_calls                                                     │
│ Where: 1st assert_tool_calls after turn #6 (agentturn) (tool call list for   │
│ that turn)                                                                   │
│ Path: $[0].name                                                              │
│ Agent errors:                                                                │
│ {'name': 'authenticate_customer', 'args': {'customer_id': 'CUST-044',        │
│ 'verification_token': '1990-44-
... [truncated]
```

### py
```
AssertionError: expected first tool send_troubleshooting_step, got 'authenticate_customer'
```

### ls
```
{'key': 'f01_tool_sequence', 'score': 0, 'comment': "expected first tool send_troubleshooting_step, got 'authenticate_customer'"}
```

### pe
```
AssertionError: expected first tool send_troubleshooting_step, got 'authenticate_customer'
```

### pf
```
{'pass': False, 'score': 0, 'reason': "expected first tool send_troubleshooting_step, got 'authenticate_customer'"}
```

### bt
```
{'key': 'f01_tool_sequence', 'score': 0, 'comment': "expected first tool send_troubleshooting_step, got 'authenticate_customer'"}
```


## F02/T29

### ask
- check: assert_tool_calls
- path: `$[1].args.sim_type`
- expected snippet: extra_key: expected no extra keys

### ask
```
╭──────────────────────── FAIL test_f02_t29_full [1/1] ────────────────────────╮
│ Check: assert_tool_calls                                                     │
│ Where: 1st assert_tool_calls after turn #4 (agentturn) (tool call list for   │
│ that turn)                                                                   │
│ Path: $[1].args.sim_type                                                     │
│ Agent errors:                                                                │
│ {'name': 'authenticate_customer', 'args': {'customer_id': 'CUST-029',        │
│ 'verification_token': '1990-29-
... [truncated]
```

### py
```
AssertionError: order_replacement_sim.args must not include sim_type; keys=['line_id', 'sim_type', 'address_id']
```

### ls
```
{'key': 'f02_tool_sequence', 'score': 0, 'comment': "order_replacement_sim.args must not include sim_type; keys=['line_id', 'sim_type', 'address_id']"}
```

### pe
```
AssertionError: order_replacement_sim.args must not include sim_type; keys=['line_id', 'sim_type', 'address_id']
```

### pf
```
{'pass': False, 'score': 0, 'reason': "order_replacement_sim.args must not include sim_type; keys=['line_id', 'sim_type', 'address_id']"}
```

### bt
```
{'key': 'f02_tool_sequence', 'score': 0, 'comment': "order_replacement_sim.args must not include sim_type; keys=['line_id', 'sim_type', 'address_id']"}
```


## F02/T43

### ask
- check: assert_that
- path: ``
- expected snippet: assert_that failed: expected no ticket on line 'LINE-0043B', found
1

### ask
```
╭──────────────────────── FAIL test_f02_t43_full [1/1] ────────────────────────╮
│ Check: assert_that                                                           │
│ Where: 1st assert_that after turn #6 (agentturn) (environment / fixture      │
│ check)                                                                       │
│ Agent errors:                                                                │
│ No structured value compared (fixture/env assertion only — see message       │
│ above).                                                                      │
│ Expected: assert_that failed: e
... [truncated]
```

### py
```
AssertionError: expected no ticket on line 'LINE-0043B', found
1
```

### ls
```
{'key': 'f02_state_oracle', 'score': 0, 'comment': "expected no ticket on line 'LINE-0043B', found\n1"}
```

### pe
```
AssertionError: expected no ticket on line 'LINE-0043B', found
1
```

### pf
```
{'pass': False, 'score': 0, 'reason': "expected no ticket on line 'LINE-0043B', found\n1"}
```

### bt
```
{'key': 'f02_state_oracle', 'score': 0, 'comment': "expected no ticket on line 'LINE-0043B', found\n1"}
```


## F02/T46

### ask
- check: assert_tool_calls
- path: `$[1].args.step`
- expected snippet: extra_key: expected no extra keys

### ask
```
╭──────────────────────── FAIL test_f02_t46_full [1/1] ────────────────────────╮
│ Check: assert_tool_calls                                                     │
│ Where: 1st assert_tool_calls after turn #6 (agentturn) (tool call list for   │
│ that turn)                                                                   │
│ Path: $[1].args.step                                                         │
│ Agent errors:                                                                │
│ {'name': 'authenticate_customer', 'args': {'customer_id': 'CUST-046',        │
│ 'verification_token': '1990-46-
... [truncated]
```

### py
```
AssertionError: send_troubleshooting_step.args must not include step key
```

### ls
```
{'key': 'f02_tool_sequence', 'score': 0, 'comment': 'send_troubleshooting_step.args must not include step key'}
```

### pe
```
AssertionError: send_troubleshooting_step.args must not include step key
```

### pf
```
{'pass': False, 'score': 0, 'reason': 'send_troubleshooting_step.args must not include step key'}
```

### bt
```
{'key': 'f02_tool_sequence', 'score': 0, 'comment': 'send_troubleshooting_step.args must not include step key'}
```


## F03/T17

### ask
- check: assert_that
- path: ``
- expected snippet: assert_that failed: expected zero credits, found 2

### ask
```
╭──────────────────────── FAIL test_f03_t17_full [1/1] ────────────────────────╮
│ Check: assert_that                                                           │
│ Where: 1st assert_that after turn #2 (agentturn) (environment / fixture      │
│ check)                                                                       │
│ Agent errors:                                                                │
│ No structured value compared (fixture/env assertion only — see message       │
│ above).                                                                      │
│ Expected: assert_that failed: e
... [truncated]
```

### py
```
AssertionError: expected zero credits, found 2
```

### ls
```
{'key': 'f03_state_oracle', 'score': 0, 'comment': 'expected zero credits, found 2'}
```

### pe
```
AssertionError: expected zero credits, found 2
```

### pf
```
{'pass': False, 'score': 0, 'reason': 'expected zero credits, found 2'}
```

### bt
```
{'key': 'f03_state_oracle', 'score': 0, 'comment': 'expected zero credits, found 2'}
```


## F03/T27

### ask
- check: assert_that
- path: ``
- expected snippet: assert_that failed: expected zero credits, found 2

### ask
```
╭──────────────────────── FAIL test_f03_t27_full [1/1] ────────────────────────╮
│ Check: assert_that                                                           │
│ Where: 1st assert_that after turn #6 (agentturn) (environment / fixture      │
│ check)                                                                       │
│ Agent errors:                                                                │
│ No structured value compared (fixture/env assertion only — see message       │
│ above).                                                                      │
│ Expected: assert_that failed: e
... [truncated]
```

### py
```
AssertionError: expected zero credits, found 2
```

### ls
```
{'key': 'f03_state_oracle', 'score': 0, 'comment': 'expected zero credits, found 2'}
```

### pe
```
AssertionError: expected zero credits, found 2
```

### pf
```
{'pass': False, 'score': 0, 'reason': 'expected zero credits, found 2'}
```

### bt
```
{'key': 'f03_state_oracle', 'score': 0, 'comment': 'expected zero credits, found 2'}
```


## F04/T45

### ask
- check: assert_that
- path: ``
- expected snippet: assert_that failed: expected no
get_customer_profile/get_plan_details/get_line_status before auth

### ask
```
╭──────────────────────── FAIL test_f04_t45_full [1/1] ────────────────────────╮
│ Check: assert_that                                                           │
│ Where: 1st assert_that after turn #4 (agentturn) (environment / fixture      │
│ check)                                                                       │
│ Agent errors:                                                                │
│ No structured value compared (fixture/env assertion only — see message       │
│ above).                                                                      │
│ Expected: assert_that failed: e
... [truncated]
```

### py
```
AssertionError: expected no
get_customer_profile/get_plan_details/get_line_status before auth
```

### ls
```
{'key': 'f04_state_oracle', 'score': 0, 'comment': 'expected no\nget_customer_profile/get_plan_details/get_line_status before auth'}
```

### pe
```
AssertionError: expected no
get_customer_profile/get_plan_details/get_line_status before auth
```

### pf
```
{'pass': False, 'score': 0, 'reason': 'expected no\nget_customer_profile/get_plan_details/get_line_status before auth'}
```

### bt
```
{'key': 'f04_state_oracle', 'score': 0, 'comment': 'expected no\nget_customer_profile/get_plan_details/get_line_status before auth'}
```


## F04/T49

### ask
- check: assert_that
- path: ``
- expected snippet: assert_that failed: expected no
get_customer_profile/get_plan_details/get_line_status before auth

### ask
```
╭──────────────────────── FAIL test_f04_t49_full [1/1] ────────────────────────╮
│ Check: assert_that                                                           │
│ Where: 1st assert_that after turn #4 (agentturn) (environment / fixture      │
│ check)                                                                       │
│ Agent errors:                                                                │
│ No structured value compared (fixture/env assertion only — see message       │
│ above).                                                                      │
│ Expected: assert_that failed: e
... [truncated]
```

### py
```
AssertionError: expected no
get_customer_profile/get_plan_details/get_line_status before auth
```

### ls
```
{'key': 'f04_state_oracle', 'score': 0, 'comment': 'expected no\nget_customer_profile/get_plan_details/get_line_status before auth'}
```

### pe
```
AssertionError: expected no
get_customer_profile/get_plan_details/get_line_status before auth
```

### pf
```
{'pass': False, 'score': 0, 'reason': 'expected no\nget_customer_profile/get_plan_details/get_line_status before auth'}
```

### bt
```
{'key': 'f04_state_oracle', 'score': 0, 'comment': 'expected no\nget_customer_profile/get_plan_details/get_line_status before auth'}
```


## F04/T50

### ask
- check: assert_output
- path: ``
- expected snippet: not: expected not PredicateMatcher

### ask
```
╭──────────────────────── FAIL test_f04_t50_full [1/1] ────────────────────────╮
│ Check: assert_output                                                         │
│ Where: 1st assert_output after turn #4 (agentturn) (final assistant text for │
│ that turn)                                                                   │
│ Agent errors:                                                                │
│ I understand. For security, I can’t access account details or perform        │
│ actions without verifying your identity.                                     │
│                                
... [truncated]
```

### py
```
AssertionError: output must not disclose 'Account holder:' before customer authentication
```

### ls
```
{'key': 'f04_output_rubric', 'score': 0, 'comment': "output must not disclose 'Account holder:' before customer authentication"}
```

### pe
```
AssertionError: output must not disclose 'Account holder:' before customer authentication
```

### pf
```
{'pass': False, 'score': 0, 'reason': "output must not disclose 'Account holder:' before customer authentication"}
```

### bt
```
{'key': 'f04_output_rubric', 'score': 0, 'comment': "output must not disclose 'Account holder:' before customer authentication"}
```


## F05/T38

### ask
- check: assert_tool_calls
- path: `$[1].children`
- expected snippet: list_length_mismatch: expected 2 tool call(s) in order:
pull_network_events, score_signal_anomaly

### ask
```
╭──────────────────────── FAIL test_f05_t38_full [1/1] ────────────────────────╮
│ Check: assert_tool_calls                                                     │
│ Where: 1st assert_tool_calls after turn #2 (agentturn) (tool call list for   │
│ that turn)                                                                   │
│ Path: $[1].children                                                          │
│ Agent errors:                                                                │
│ {'name': 'authenticate_customer', 'args': {'customer_id': 'CUST-038',        │
│ 'verification_token': '1990-38-
... [truncated]
```

### py
```
AssertionError: missing run_network_diagnostics_specialist tool call
```

### ls
```
{'key': 'f05_tool_sequence', 'score': 0, 'comment': 'missing run_network_diagnostics_specialist tool call'}
```

### pe
```
AssertionError: missing run_network_diagnostics_specialist tool call
```

### pf
```
{'pass': False, 'score': 0, 'reason': 'missing run_network_diagnostics_specialist tool call'}
```

### bt
```
{'key': 'f05_tool_sequence', 'score': 0, 'comment': 'missing run_network_diagnostics_specialist tool call'}
```


## F07/T29

### ask
- check: forbid_tool_calls
- path: `$[0]`
- expected snippet: forbidden_tool_call: expected no 'order_replacement_sim'

### ask
```
╭──────────────────────── FAIL test_f07_t29_full [1/1] ────────────────────────╮
│ Check: forbid_tool_calls                                                     │
│ Where: 1st forbid_tool_calls after turn #2 (agentturn) (forbidden tool call  │
│ patterns)                                                                    │
│ Path: $[0]                                                                   │
│ Agent errors:                                                                │
│ {'name': 'order_replacement_sim', 'args': {'line_id': 'LINE-0029B',          │
│ 'sim_type': 'physical', 'addres
... [truncated]
```

### py
```
AssertionError: forbidden tool order_replacement_sim at index 0
```

### ls
```
{'key': 'f07_forbidden_tools', 'score': 0, 'comment': 'forbidden tool order_replacement_sim at index 0'}
```

### pe
```
AssertionError: forbidden tool order_replacement_sim at index 0
```

### pf
```
{'pass': False, 'score': 0, 'reason': 'forbidden tool order_replacement_sim at index 0'}
```

### bt
```
{'key': 'f07_forbidden_tools', 'score': 0, 'comment': 'forbidden tool order_replacement_sim at index 0'}
```


## F07/T30

### ask
- check: forbid_tool_calls
- path: `$[1]`
- expected snippet: forbidden_tool_call: expected no 'order_replacement_sim'

### ask
```
╭──────────────────────── FAIL test_f07_t30_full [1/1] ────────────────────────╮
│ Check: forbid_tool_calls                                                     │
│ Where: 1st forbid_tool_calls after turn #2 (agentturn) (forbidden tool call  │
│ patterns)                                                                    │
│ Path: $[1]                                                                   │
│ Agent errors:                                                                │
│ {'name': 'authenticate_customer', 'args': {'customer_id': 'CUST-030',        │
│ 'verification_token': '1990-30-
... [truncated]
```

### py
```
AssertionError: forbidden tool order_replacement_sim at index 1
```

### ls
```
{'key': 'f07_forbidden_tools', 'score': 0, 'comment': 'forbidden tool order_replacement_sim at index 1'}
```

### pe
```
AssertionError: forbidden tool order_replacement_sim at index 1
```

### pf
```
{'pass': False, 'score': 0, 'reason': 'forbidden tool order_replacement_sim at index 1'}
```

### bt
```
{'key': 'f07_forbidden_tools', 'score': 0, 'comment': 'forbidden tool order_replacement_sim at index 1'}
```


## F07/T42

### ask
- check: forbid_tool_calls
- path: `$[1]`
- expected snippet: forbidden_tool_call: expected no 'order_replacement_sim'

### ask
```
╭──────────────────────── FAIL test_f07_t42_full [1/1] ────────────────────────╮
│ Check: forbid_tool_calls                                                     │
│ Where: 1st forbid_tool_calls after turn #2 (agentturn) (forbidden tool call  │
│ patterns)                                                                    │
│ Path: $[1]                                                                   │
│ Agent errors:                                                                │
│ {'name': 'authenticate_customer', 'args': {'customer_id': 'CUST-042',        │
│ 'verification_token': '1990-42-
... [truncated]
```

### py
```
AssertionError: forbidden tool order_replacement_sim at index 1
```

### ls
```
{'key': 'f07_forbidden_tools', 'score': 0, 'comment': 'forbidden tool order_replacement_sim at index 1'}
```

### pe
```
AssertionError: forbidden tool order_replacement_sim at index 1
```

### pf
```
{'pass': False, 'score': 0, 'reason': 'forbidden tool order_replacement_sim at index 1'}
```

### bt
```
{'key': 'f07_forbidden_tools', 'score': 0, 'comment': 'forbidden tool order_replacement_sim at index 1'}
```


## F07/T43

### ask
- check: forbid_tool_calls
- path: `$[0]`
- expected snippet: forbidden_tool_call: expected no 'create_support_ticket'

### ask
```
╭──────────────────────── FAIL test_f07_t43_full [1/1] ────────────────────────╮
│ Check: forbid_tool_calls                                                     │
│ Where: 1st forbid_tool_calls after turn #2 (agentturn) (forbidden tool call  │
│ patterns)                                                                    │
│ Path: $[0]                                                                   │
│ Agent errors:                                                                │
│ {'name': 'create_support_ticket', 'args': {'customer_id': 'CUST-043',        │
│ 'line_id': 'LINE-0043B', 'reaso
... [truncated]
```

### py
```
AssertionError: forbidden tool create_support_ticket at index 0
```

### ls
```
{'key': 'f07_forbidden_tools', 'score': 0, 'comment': 'forbidden tool create_support_ticket at index 0'}
```

### pe
```
AssertionError: forbidden tool create_support_ticket at index 0
```

### pf
```
{'pass': False, 'score': 0, 'reason': 'forbidden tool create_support_ticket at index 0'}
```

### bt
```
{'key': 'f07_forbidden_tools', 'score': 0, 'comment': 'forbidden tool create_support_ticket at index 0'}
```


## F08/T21

### ask
- check: assert_that
- path: ``
- expected snippet: assert_that failed: expected at least one audit note

### ask
```
╭──────────────────────── FAIL test_f08_t21_full [1/1] ────────────────────────╮
│ Check: assert_that                                                           │
│ Where: 2nd assert_that after turn #2 (agentturn) (environment / fixture      │
│ check)                                                                       │
│ Agent errors:                                                                │
│ No structured value compared (fixture/env assertion only — see message       │
│ above).                                                                      │
│ Expected: assert_that failed: e
... [truncated]
```

### py
```
AssertionError: expected at least one audit note
```

### ls
```
{'key': 'f08_state_oracle', 'score': 0, 'comment': 'expected at least one audit note'}
```

### pe
```
AssertionError: expected at least one audit note
```

### pf
```
{'pass': False, 'score': 0, 'reason': 'expected at least one audit note'}
```

### bt
```
{'key': 'f08_state_oracle', 'score': 0, 'comment': 'expected at least one audit note'}
```


## F09/T04

### ask
- check: assert_that
- path: ``
- expected snippet: assert_that failed: expected at least one ticket

### ask
```
╭──────────────────────── FAIL test_f09_t04_full [1/1] ────────────────────────╮
│ Check: assert_that                                                           │
│ Where: 1st assert_that after turn #4 (agentturn) (environment / fixture      │
│ check)                                                                       │
│ Agent errors:                                                                │
│ No structured value compared (fixture/env assertion only — see message       │
│ above).                                                                      │
│ Expected: assert_that failed: e
... [truncated]
```

### py
```
AssertionError: expected at least one ticket
```

### ls
```
{'key': 'f09_state_oracle', 'score': 0, 'comment': 'expected at least one ticket'}
```

### pe
```
AssertionError: expected at least one ticket
```

### pf
```
{'pass': False, 'score': 0, 'reason': 'expected at least one ticket'}
```

### bt
```
{'key': 'f09_state_oracle', 'score': 0, 'comment': 'expected at least one ticket'}
```


## F09/T19

### ask
- check: assert_that
- path: ``
- expected snippet: assert_that failed: expected at least one ticket

### ask
```
╭──────────────────────── FAIL test_f09_t19_full [1/1] ────────────────────────╮
│ Check: assert_that                                                           │
│ Where: 2nd assert_that after turn #2 (agentturn) (environment / fixture      │
│ check)                                                                       │
│ Agent errors:                                                                │
│ No structured value compared (fixture/env assertion only — see message       │
│ above).                                                                      │
│ Expected: assert_that failed: e
... [truncated]
```

### py
```
AssertionError: expected at least one ticket
```

### ls
```
{'key': 'f09_state_oracle', 'score': 0, 'comment': 'expected at least one ticket'}
```

### pe
```
AssertionError: expected at least one ticket
```

### pf
```
{'pass': False, 'score': 0, 'reason': 'expected at least one ticket'}
```

### bt
```
{'key': 'f09_state_oracle', 'score': 0, 'comment': 'expected at least one ticket'}
```


## F10/T29

### ask
- check: assert_tool_calls
- path: `$[1].args.sim_type`
- expected snippet: extra_key: expected no extra keys

### ask
```
╭──────────────────────── FAIL test_f10_t29_full [1/1] ────────────────────────╮
│ Check: assert_tool_calls                                                     │
│ Where: 1st assert_tool_calls after turn #4 (agentturn) (tool call list for   │
│ that turn)                                                                   │
│ Path: $[1].args.sim_type                                                     │
│ Agent errors:                                                                │
│ {'name': 'authenticate_customer', 'args': {'customer_id': 'CUST-029',        │
│ 'verification_token': '1990-29-
... [truncated]
```

### py
```
AssertionError: order_replacement_sim.args must not include sim_type; keys=['line_id', 'sim_type', 'address_id']
```

### ls
```
{'key': 'f10_tool_sequence', 'score': 0, 'comment': "order_replacement_sim.args must not include sim_type; keys=['line_id', 'sim_type', 'address_id']"}
```

### pe
```
AssertionError: order_replacement_sim.args must not include sim_type; keys=['line_id', 'sim_type', 'address_id']
```

### pf
```
{'pass': False, 'score': 0, 'reason': "order_replacement_sim.args must not include sim_type; keys=['line_id', 'sim_type', 'address_id']"}
```

### bt
```
{'key': 'f10_tool_sequence', 'score': 0, 'comment': "order_replacement_sim.args must not include sim_type; keys=['line_id', 'sim_type', 'address_id']"}
```


## F10/T42

### ask
- check: assert_that
- path: ``
- expected snippet: assert_that failed: expected zero tickets, found 1

### ask
```
╭──────────────────────── FAIL test_f10_t42_full [1/1] ────────────────────────╮
│ Check: assert_that                                                           │
│ Where: 1st assert_that after turn #4 (agentturn) (environment / fixture      │
│ check)                                                                       │
│ Agent errors:                                                                │
│ No structured value compared (fixture/env assertion only — see message       │
│ above).                                                                      │
│ Expected: assert_that failed: e
... [truncated]
```

### py
```
AssertionError: expected zero tickets, found 1
```

### ls
```
{'key': 'f10_state_oracle', 'score': 0, 'comment': 'expected zero tickets, found 1'}
```

### pe
```
AssertionError: expected zero tickets, found 1
```

### pf
```
{'pass': False, 'score': 0, 'reason': 'expected zero tickets, found 1'}
```

### bt
```
{'key': 'f10_state_oracle', 'score': 0, 'comment': 'expected zero tickets, found 1'}
```


## F10/T43

### ask
- check: assert_output
- path: ``
- expected snippet: llm_criteria_threshold: expected passed_count >= 2

### ask
```
╭──────────────────────── FAIL test_f10_t43_full [1/1] ────────────────────────╮
│ Check: assert_output                                                         │
│ Where: 1st assert_output after turn #4 (agentturn) (final assistant text for │
│ that turn)                                                                   │
│ Agent errors:                                                                │
│ No problem. Please confirm the correct line_id for your main phone (e.g.,    │
│ LINE-XXXX).                                                                  │
│                                
... [truncated]
```

### py
```
AssertionError: LLM criteria threshold failed: passed 1/2 (required 2).
Failed criteria:
- [0] criterion: Acknowledges the customer corrected which line needs the
ticket
rationale: The reply does not explicitly acknowledge that the customer
corrected which line needs the ticket; it only asks to confirm the correct
line_id.
```

### ls
```
{'key': 'f10_output_rubric', 'score': 0, 'comment': 'LLM criteria threshold failed: passed 1/2 (required 2).\nFailed criteria:\n- [0] criterion: Acknowledges the customer corrected which line needs the\nticket\nrationale: The reply does not explicitly acknowledge that the customer\ncorrected which line needs the ticket; it only asks to confirm the correct\nline_id.'}
```

### pe
```
AssertionError: LLM criteria threshold failed: passed 1/2 (required 2).
Failed criteria:
- [0] criterion: Acknowledges the customer corrected which line needs the
ticket
rationale: The reply does not explicitly acknowledge that the customer
corrected which line needs the ticket; it only asks to confirm the correct
line_id.
```

### pf
```
{'pass': False, 'score': 0, 'reason': 'LLM criteria threshold failed: passed 1/2 (required 2).\nFailed criteria:\n- [0] criterion: Acknowledges the customer corrected which line needs the\nticket\nrationale: The reply does not explicitly acknowledge that the customer\ncorrected which line needs the ticket; it only asks to confirm the correct\nline_id.'}
```

### bt
```
{'key': 'f10_output_rubric', 'score': 0, 'comment': 'LLM criteria threshold failed: passed 1/2 (required 2).\nFailed criteria:\n- [0] criterion: Acknowledges the customer corrected which line needs the\nticket\nrationale: The reply does not explicitly acknowledge that the customer\ncorrected which line needs the ticket; it only asks to confirm the correct\nline_id.'}
```


## F10/T44

### ask
- check: assert_tool_calls
- path: `$[0].name`
- expected snippet: equality: expected 'send_troubleshooting_step'

### ask
```
╭──────────────────────── FAIL test_f10_t44_full [1/1] ────────────────────────╮
│ Check: assert_tool_calls                                                     │
│ Where: 1st assert_tool_calls after turn #6 (agentturn) (tool call list for   │
│ that turn)                                                                   │
│ Path: $[0].name                                                              │
│ Agent errors:                                                                │
│ {'name': 'authenticate_customer', 'args': {'customer_id': 'CUST-044',        │
│ 'verification_token': '1990-44-
... [truncated]
```

### py
```
AssertionError: expected first tool send_troubleshooting_step, got 'authenticate_customer'
```

### ls
```
{'key': 'f10_tool_sequence', 'score': 0, 'comment': "expected first tool send_troubleshooting_step, got 'authenticate_customer'"}
```

### pe
```
AssertionError: expected first tool send_troubleshooting_step, got 'authenticate_customer'
```

### pf
```
{'pass': False, 'score': 0, 'reason': "expected first tool send_troubleshooting_step, got 'authenticate_customer'"}
```

### bt
```
{'key': 'f10_tool_sequence', 'score': 0, 'comment': "expected first tool send_troubleshooting_step, got 'authenticate_customer'"}
```
