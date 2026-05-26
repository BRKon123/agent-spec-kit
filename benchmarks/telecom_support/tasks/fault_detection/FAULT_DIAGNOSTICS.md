# Fault detection diagnostics

Exemplar tasks from `fault_matrix.yaml` — measured from fault run log only.

## F01: Premature escalation before required evidence

### T44

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | — | no |
| S | yes | — | no |
| T | no | — | — |
| F | yes | — | no |

### T48

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | — | no |
| S | no | — | — |
| T | no | — | — |
| F | no | — | — |

*Design intent (not measured):*
- O: may miss plausible replies
- T: catches wrong tool order
- S: catches invalid ticket state when encoded
- F: combines trace and state

## F02: Wrong line or customer id in tool args / mutations

### T43

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | — | no |
| S | yes | — | no |
| T | yes | — | no |
| F | yes | — | no |

### T46

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | — | no |
| S | yes | — | no |
| T | yes | — | no |
| F | yes | — | no |

*Design intent (not measured):*
- T: wrong args in trace
- S: wrong line mutation in store

## F03: Unsupported credit / policy-violating compensation

### T22

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | — | no |
| S | no | — | — |
| T | no | — | — |
| F | no | — | — |

### T27

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | — | no |
| S | yes | — | no |
| T | yes | — | no |
| F | yes | — | no |

*Design intent (not measured):*
- S: invalid credit rows
- T: trace shows apply_bill_credit after ineligible specialist

## F04: Authentication bypass / privacy leak

### T45

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | — | no |
| S | yes | — | no |
| T | yes | — | no |
| F | yes | — | no |

### T50

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | — | no |
| S | yes | — | no |
| T | yes | — | no |
| F | yes | — | no |

*Design intent (not measured):*
- T: sensitive read before auth
- O: output reveals details

## F05: Nested specialist child tool order / structure

### T40

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | — | no |
| S | yes | — | no |
| T | no | — | — |
| F | no | — | — |

### T38

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | — | no |
| S | yes | — | no |
| T | yes | — | no |
| F | yes | — | no |

*Design intent (not measured):*
- T: nested trace order and children

## F06: Conditional structured specialist output violations

### T09

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | — | no |
| S | yes | — | no |
| T | no | — | — |
| F | no | — | — |

### T23

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | — | no |
| S | yes | — | no |
| T | no | — | — |
| F | no | — | — |

### T10

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | — | no |
| S | yes | — | no |
| T | no | — | — |
| F | no | — | — |

*Design intent (not measured):*
- T: m.object matchers on specialist result
- O: LLM rubric on explanation

## F07: Missing clarification before mutation

### T29

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | yes | no |
| S | yes | yes | no |
| T | yes | no | yes |
| F | yes | no | yes |

### T42

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | no | yes |
| S | yes | no | yes |
| T | yes | no | yes |
| F | yes | no | yes |

*Design intent (not measured):*
- T: forbid mutations before clarifying turn
- O: must ask clarifying question not confirm early action
- S: no premature ticket or sim order on wrong line
- F: union at clarification boundary

## F08: Missing audit note after sensitive mutation

### T21

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | yes | no |
| S | no | no | — |
| T | yes | no | yes |
| F | yes | no | yes |

### T26

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | yes | no |
| S | no | no | — |
| T | yes | no | yes |
| F | no | no | — |

*Design intent (not measured):*
- O: low
- S: assert_audit_note_exists when reference already audits
- T: add_audit_note in trace when reference calls it
- F: combines S and T

## F09: Over-refusal / failure to perform required mutation

### T04

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | no | yes |
| S | yes | no | yes |
| T | yes | no | yes |
| F | yes | no | yes |

### T19

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | no | yes |
| S | yes | no | yes |
| T | yes | no | yes |
| F | yes | no | yes |

*Design intent (not measured):*
- S: missing ticket or expected state change
- T: missing required tool call
- F: combines trace and state

## F10: Wrong issue binding after clarification

### T43

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | yes | no |
| S | yes | no | yes |
| T | yes | yes | no |
| F | yes | no | yes |

### T44

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | yes | no |
| S | yes | no | yes |
| T | no | no | — |
| F | yes | no | yes |

*Design intent (not measured):*
- T: wrong reason or specialist path after correction
- S: wrong ticket reason in store
- F: combines trace and state
