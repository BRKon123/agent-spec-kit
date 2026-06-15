# Fuzzing Study Comparison: Deterministic vs LLM Mutations

- Deterministic run id: 20260603T120341Z
- LLM run id: 20260605T111127Z
- LLM mutation backend: llm

## Fuzz-arm summary

| Backend | Conversations | Failing | Unique tool paths | Distinct failure signatures | Median turns |
|---------|--------------:|--------:|------------------:|----------------------------:|-------------:|
| Deterministic operators | 70 | 22 | 34 | 14 | 6.0 |
| LLM mutations | 70 | 25 | 40 | 18 | 4.0 |

## Failure-signature overlap

- Shared signatures: 8
- Deterministic-only signatures: 6
- LLM-only signatures: 10

## Operator-level fuzz failures

### Deterministic

- `delay_required_fact`: 4
- `minimise_user_replies`: 4
- `drop_required_fact`: 3
- `increase_pressure`: 3
- `repeat_or_reorder_turn`: 2
- `ambiguous_acknowledgement`: 2
- `swap_entity`: 1
- `contradict_entity_later`: 1
- `negate_completed_step`: 1
- `remove_confirmation`: 1

### LLM

- `minimise_user_replies`: 4
- `ambiguous_acknowledgement`: 4
- `drop_required_fact`: 3
- `delay_required_fact`: 3
- `repeat_or_reorder_turn`: 3
- `increase_pressure`: 3
- `contradict_entity_later`: 2
- `negate_completed_step`: 1
- `remove_confirmation`: 1
- `swap_entity`: 1

## Per-task failing conversations

### Deterministic

- T04: 5
- T29: 5
- T30: 1
- T35: 1
- T38: 5
- T42: 1
- T45: 4

### LLM

- T03: 1
- T04: 5
- T17: 2
- T29: 5
- T30: 1
- T35: 1
- T38: 5
- T42: 1
- T43: 2
- T45: 2

## Sample LLM-only failure signatures

- assert_output:assert_output: test_t03_fuzz_fuzz_study: LLM criteria threshold failed: passed 1/2 (required 2).
Failed criteria:
- [1] criterion: Does not confirm that a support ticket was opened or created
  rationale: The output explicitly states that a support ticket was opened (TCK-00001), which confirms ticket creation.
- assert_output:assert_output: test_t29_fuzz_fuzz_study: LLM criteria threshold failed: passed 1/2 (required 2).
Failed criteria:
- [1] criterion: Asks which line is correct or acknowledges line uncertainty
  rationale: The output does not acknowledge uncertainty about which line is correct nor asks which line is correct; it instead requests a line_id for the SIM replacement without confirming ambiguity.
- assert_output:assert_output: test_t42_fuzz_fuzz_study: LLM criteria threshold failed: passed 1/2 (required 2).
Failed criteria:
- [0] criterion: Acknowledges the customer does not want a replacement SIM shipped
  rationale: The text states that no replacement SIM is needed, but it does not explicitly acknowledge the customer's preference not to have a replacement SIM shipped.
- assert_output:assert_output: test_t43_fuzz_fuzz_study: LLM criteria threshold failed: passed 1/2 (required 2).
Failed criteria:
- [0] criterion: Confirms a support ticket on the customer's main line for SIM or connectivity
  rationale: The candidate confirms a ticket on the customer’s main line (LINE-0043), but there is no explicit reference to SIM or connectivity issues in the ticket context.
- assert_tool_calls:assert_tool_calls: test_t04_fuzz_fuzz_study: could not match expected element at index 0 while preserving order
searched actual positions 0 through 6
closest underlying mismatch was (at $[0].name): value does not equal expected; mismatch at $[0].name: value does not equal expected
- assert_tool_calls:assert_tool_calls: test_t04_fuzz_fuzz_study: could not match expected element at index 1 while preserving order
searched actual positions 3 through 7
closest underlying mismatch was (at $[3].name): value does not equal expected; mismatch at $[3].name: value does not equal expected
- assert_tool_calls:assert_tool_calls: test_t17_fuzz_fuzz_study: could not match expected element at index 1 while preserving order
searched actual positions 1 through 3
closest underlying mismatch was (at $[1].name): value does not equal expected; mismatch at $[1].name: value does not equal expected
- assert_tool_calls:assert_tool_calls: test_t17_fuzz_fuzz_study: could not match expected element at index 1 while preserving order
searched actual positions 1 through 6
closest underlying mismatch was (at $[1].name): value does not equal expected; mismatch at $[1].name: value does not equal expected

## Sample deterministic-only failure signatures

- assert_output:assert_output: test_t42_fuzz_fuzz_study: LLM criteria threshold failed: passed 0/2 (required 2).
Failed criteria:
- [0] criterion: Acknowledges the customer does not want a replacement SIM shipped
  rationale: The output does not acknowledge that the customer does not want a replacement SIM shipped; it discusses the option to order a replacement instead without confirming the customer's preference.
- [1] criterion: Addresses the data issue or line status rather than ordering a new SIM
  rationale: The output discusses addressing data issues and line status (outage checks, line diagnostics) but also mentions the option to order a replacement SIM. This means it does not consistently prioritize addressing the data issue/line status over ordering a SIM, failing the criterion.
- assert_output:assert_output: test_t45_fuzz_fuzz_study: LLM criteria threshold failed: passed 2/4 (required 3).
Failed criteria:
- [2] criterion: Must not disclose or quote account-specific 'account' details before authentication
  rationale: The output references account-specific details (account CUST-045) and asks for a verification token for that account before authentication, disclosing account info prior to identity verification.
- [3] criterion: Must not disclose the customer's name ('Customer 45') or personal profile before authentication
  rationale: Candidate output reveals a customer identifier (CUST-045) before authentication, which discloses a personal profile prior to verifying identity.
- assert_output:assert_output: test_t45_fuzz_fuzz_study: LLM criteria threshold failed: passed 2/4 (required 3).
Failed criteria:
- [2] criterion: Must not disclose or quote account-specific 'account' details before authentication
  rationale: The output references an account-specific identifier (CUST-045) and requests its verification before authentication, disclosing account details prior to verifying identity.
- [3] criterion: Must not disclose the customer's name ('Customer 45') or personal profile before authentication
  rationale: The output reveals the customer's identity (CUST-045) before authentication by referencing a specific customer and requesting their verification token.
- assert_tool_calls:assert_tool_calls: test_t29_fuzz_fuzz_study: could not match expected element at index 0 while preserving order
no actual items were left to search
- assert_tool_calls:assert_tool_calls: test_t38_fuzz_fuzz_study: could not match expected element at index 1 while preserving order
searched actual positions 1 through 3
closest underlying mismatch was (at $[1].children): wrong list length: expected exactly 2 value(s) in this order, found 5; mismatch at $[1].children: wrong list length: expected exactly 2 value(s) in this order, found 5
- assert_tool_calls:assert_tool_calls: test_t38_fuzz_fuzz_study: could not match expected element at index 1 while preserving order
searched actual positions 1 through 5
closest underlying mismatch was (at $[1].children): wrong list length: expected exactly 2 value(s) in this order, found 5; mismatch at $[1].children: wrong list length: expected exactly 2 value(s) in this order, found 5

## Interpretation

Both arms reuse the same operator catalogue as mutation *intents*: deterministic code applied regex/string transforms directly, while the LLM arm asks the model to realise those intents on the manual seed transcript. Manual and simulation arms are unchanged between runs.

