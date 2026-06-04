# Manual failure-specificity classification (A–E)

Graded by reading each captured string in [`failures_samples.yaml`](failures_samples.yaml) against the rubric in [`EXPRESSIVENESS_TABLE.md`](EXPRESSIVENESS_TABLE.md). **Not** auto-scored from keywords (e.g. `path=` on ask only).

Framework order in rows: **ask / py / ls / pe / pf / bt**.

## Rubric

| Grade | When we assign it |
| --- | --- |
| **A** | Stable location in the trace/value **plus** expected vs actual (or equivalent path witness). |
| **B** | Plain-language rule, tool, field, or value slice in the message (e.g. forbidden tool name, `line_id` expected/got, validation path) — **no** structured JSON path witness. |
| **C** | Only which check/scorer failed (evaluator `key` + `score: 0`, assert type label) **without** naming the violating tool, field, or expected/actual values. |
| **D** | Generic shell: bare `AssertionError`, empty assert, or class-only validation with no field witness. |
| **E** | Opaque boolean only. *(None observed.)* |

---

## C01 — final output rubric

| Framework | Message (summary) | Grade | Why |
| --- | --- | ---: | --- |
| ask | `path=$` `one_of` — expected rubric matchers vs actual billing-safe output | **A** | Output path + expected options vs actual text. |
| pytest | `AssertionError` (empty) | **D** | No rubric clause, no expected/actual surfaced. |
| langsmith | `output_rubric`, score 0 | **B** | Names failing evaluator; no path or values. |
| pydantic | `AssertionError` (empty) | **D** | Same as pytest. |
| promptfoo | `assertion returned False` | **D** | Harness boolean only. |
| braintrust | `c01`, score 0 | **B** | Named scorer only. |

**Row:** `A/D/B/D/D/B`

---

## C02 — structured object shape (tool list / severity)

| Framework | Message (summary) | Grade | Why |
| --- | --- | ---: | --- |
| ask | `path=$[0]` `missing_element` — actual tools include `severity: lo...`, expected match at index 0 | **A** | Tool-list path + expected/actual slice (shape/severity witness). |
| pytest | `AssertionError` (empty) | **D** | Shape check failed internally; no keys or severity in message. |
| langsmith | `object_shape`, score 0 | **B** | Which check failed; no field-level diff. |
| pydantic | `AssertionError` (empty) | **D** | Same as pytest. |
| promptfoo | `assertion returned False` | **D** | Generic assertion failure. |
| braintrust | `c02`, score 0 | **B** | Named scorer only. |

**Row:** `A/D/B/D/D/B`

---

## C03 — conditional object (eligible → amount)

| Framework | Message (summary) | Grade | Why |
| --- | --- | ---: | --- |
| ask | `path=$[0]` — actual shows `eligible: True` but no `amount` in billing result | **A** | Path + concrete actual object vs expected conditional shape. |
| pytest | `AssertionError` (empty) | **D** | Missing `amount` not reported in exception text. |
| langsmith | `conditional_object`, score 0 | **B** | Named evaluator; no eligible/amount witness. |
| pydantic | `AssertionError` (empty) | **D** | Same as pytest. |
| promptfoo | `assertion returned False` | **D** | Generic assertion failure. |
| braintrust | `c03`, score 0 | **B** | Named scorer only. |

**Row:** `A/D/B/D/D/B`

---

## C04 — numeric range (amount bounds)

| Framework | Message (summary) | Grade | Why |
| --- | --- | ---: | --- |
| ask | `path=$[0]` — actual `amount: 9999.0` outside expected range in tool result | **A** | Path + actual numeric value in witness (range violation visible). |
| pytest | `AssertionError` (empty) | **D** | Out-of-range amount not surfaced in message. |
| langsmith | `numeric_regex`, score 0 | **B** | Names range/regex check; no amount or bounds shown. |
| pydantic | `AssertionError` (empty) | **D** | Same as pytest. |
| promptfoo | `assertion returned False` | **D** | Generic assertion failure. |
| braintrust | `c04`, score 0 | **B** | Named scorer only. |

**Row:** `A/D/B/D/D/B`

---

## C05 — ordered tool sequence

| Framework | Message (summary) | Grade | Why |
| --- | --- | ---: | --- |
| ask | `path=$[1]` — wrong order: `get_outage_status` before `authenticate_customer`; no items left at index 1 | **A** | Path + expected subsequence vs actual tool order. |
| pytest | `AssertionError` (empty) | **D** | Sequence branch uses bare assert; order not in message. |
| langsmith | `ordered_sequence`, score 0 | **B** | Named sequence check; no tool names/order. |
| pydantic | `AssertionError` (empty) | **D** | Same as pytest. |
| promptfoo | `assertion returned False` | **D** | Generic assertion failure. |
| braintrust | `c05`, score 0 | **B** | Named scorer only. |

**Row:** `A/D/B/D/D/B`

---

## C06 — forbidden tool call

| Framework | Message (summary) | Grade | Why |
| --- | --- | ---: | --- |
| ask | `path=$[1]` `forbidden_tool_call` — expected no `apply_bill_credit`, actual credit tool at index 1 | **A** | Path + forbidden tool name + index + actual call. |
| pytest | `AssertionError` (empty) | **D** | Forbidden tool hit but not named in exception. |
| langsmith | `forbidden_tools`, score 0 | **C** | Evaluator key only; no forbidden tool name or index in message. |
| pydantic | `forbidden span apply_bill_credit present` | **B** | Names the forbidden tool in plain text. |
| promptfoo | `not-trajectory:tool-used: forbidden tool apply_bill_credit present` | **B** | Names forbidden tool and assert kind. |
| braintrust | `C06`, score 0 | **C** | Scorer id + score only; no tool witness. |

**Row:** `A/D/C/B/B/C`

---

## C07 — tool argument matching (`line_id`)

| Framework | Message (summary) | Grade | Why |
| --- | --- | ---: | --- |
| ask | `path=$[1]` — witness includes `line_id: LINE-002` vs expected `LINE-001` at tool index 1 | **A** | Path + actual arg embedded in matcher witness. |
| pytest | `get_line_status.args.line_id expected 'LINE-001', got 'LINE-002'` | **B** | Clear field + expected/actual values; no `$[1].args` path syntax. |
| langsmith | `tool_args`, score 0 | **B** | Which check failed; arg diff not in payload. |
| pydantic | Same text as pytest | **B** | Same as pytest — explicit field message. |
| promptfoo | `assertion returned False` | **D** | Does not surface `line_id` diff (unlike pytest). |
| braintrust | `c07`, score 0 | **B** | Named scorer only. |

**Row:** `A/B/B/B/D/B`

---

## C08 — tool result shape (nested specialist output)

| Framework | Message (summary) | Grade | Why |
| --- | --- | ---: | --- |
| ask | `path=$[0]` — network specialist `result` with `severity: medium` / truncated `recommended_action` vs expected | **A** | Path + actual result object slice in witness. |
| pytest | `AssertionError` (empty) | **D** | Result-field mismatch not reported in exception. |
| langsmith | `tool_result`, score 0 | **B** | Named result check; no severity/action fields. |
| pydantic | `AssertionError` (empty) | **D** | Same as pytest. |
| promptfoo | `assertion returned False` | **D** | Generic assertion failure. |
| braintrust | `c08`, score 0 | **B** | Named scorer only. |

**Row:** `A/D/B/D/D/B`

---

## C09 — nested tools (parent/child tool pattern)

| Framework | Message (summary) | Grade | Why |
| --- | --- | ---: | --- |
| ask | `path=$[0]` — latency query / `recommended_action` in actual vs expected nested tool pattern | **A** | Path + actual tool list shows wrong nested structure. |
| pytest | `AssertionError` (empty) | **D** | Nested pattern failure not described in message. |
| langsmith | `nested_tools`, score 0 | **B** | Named nested-tools check; no structure diff. |
| pydantic | `AssertionError` (empty) | **D** | Same as pytest. |
| promptfoo | `assertion returned False` | **D** | Generic assertion failure. |
| braintrust | `c09`, score 0 | **B** | Named scorer only. |

**Row:** `A/D/B/D/D/B`

---

## C10 — unordered siblings (count / pairing)

| Framework | Message (summary) | Grade | Why |
| --- | --- | ---: | --- |
| ask | `path=$` `list_too_short` expected `>= 2`, actual `1` | **A** | Path + numeric expected/actual on list length. |
| pytest | `AssertionError` (empty) | **D** | Sibling-count failure not surfaced. |
| langsmith | `unordered_siblings`, score 0 | **B** | Named check; no `>= 2` vs `1` in message. |
| pydantic | `AssertionError` (empty) | **D** | Same as pytest. |
| promptfoo | `assertion returned False` | **D** | Generic assertion failure. |
| braintrust | `c10`, score 0 | **B** | Named scorer only. |

**Row:** `A/D/B/D/D/B`

---

## C11 — DB state (support ticket exists)

| Framework | Message (summary) | Grade | Why |
| --- | --- | ---: | --- |
| ask | `expected at least one ticket` | **B** | Plain oracle rule; no table/row/path. |
| pytest | `expected at least one ticket` | **B** | Same explicit oracle text. |
| langsmith | `expected at least one ticket` | **B** | Same — rule stated, not DB coordinates. |
| pydantic | `expected at least one ticket` | **B** | Same. |
| promptfoo | `expected at least one ticket` | **B** | Same. |
| braintrust | `c11`, score 0, `note`: same ticket message | **B** | Scorer key + note repeats rule; still no row/path. |

**Row:** `B/B/B/B/B/B`

---

## C12 — multi-turn memory (missing tool on later turn)

| Framework | Message (summary) | Grade | Why |
| --- | --- | ---: | --- |
| ask | `path=$[1]` — actual only `authenticate_customer`; expected `create_support_ticket` at index 1 | **A** | Path + expected tool vs actual shortened tool list. |
| pytest | `AssertionError` (empty) | **D** | Missing ticket tool not named in exception. |
| langsmith | `multi_turn_memory`, score 0 | **B** | Named memory check; no turn/tool witness. |
| pydantic | `AssertionError` (empty) | **D** | Same as pytest. |
| promptfoo | `assertion returned False` | **D** | Generic assertion failure. |
| braintrust | `c12`, score 0 | **B** | Named scorer only. |

**Row:** `A/D/B/D/D/B`

---

## Grade matrix (all checks)

| Check | ask | py | ls | pe | pf | bt |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| C01 | A | D | B | D | D | B |
| C02 | A | D | B | D | D | B |
| C03 | A | D | B | D | D | B |
| C04 | A | D | B | D | D | B |
| C05 | A | D | B | D | D | B |
| C06 | A | D | B | D | D | B |
| C07 | A | B | B | B | D | B |
| C08 | A | D | B | D | D | B |
| C09 | A | D | B | D | D | B |
| C10 | A | D | B | D | D | B |
| C11 | B | B | B | B | B | B |
| C12 | A | D | B | D | D | B |

**Counts (framework × grade):** ask 11×A + 1×B; pytest 1×B + 11×D; langsmith 12×B; pydantic 1×B + 11×D; promptfoo 12×D; braintrust 12×B.

---

## Notes

- **ask** is the only framework that consistently reaches **A** on trajectory/value checks (built-in path witnesses).
- **pytest / pydantic** reach **B** only on **C07** because checks use an explicit `line_id expected … got …` assert; elsewhere captures are empty `AssertionError` → **D**, not **B**.
- **langsmith / braintrust** cluster at **B**: evaluator/scorer `key` (+ sometimes `note`) without path-level expected/actual.
- **promptfoo** is **D** on every check here: always `assertion returned False` with no field detail.
- **C11** is uniformly **B**: every framework surfaces the same oracle sentence.

Source of truth for `catalog.py` → `FAILURE_SPECIFICITY` and regenerated [`FAILURE_SAMPLES.md`](FAILURE_SAMPLES.md) grade lines.
