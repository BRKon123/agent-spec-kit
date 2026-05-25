# Fault detection diagnostics

Exemplar tasks from `fault_matrix.yaml` — measured from fault run log only.

## F01: Premature escalation before required evidence

### T44

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | yes | no |
| S | yes | yes | no |
| T | no | yes | — |
| F | yes | no | yes |

### T48

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | yes | no |
| S | no | no | — |
| T | no | no | — |
| F | no | no | — |

*Design intent (not measured):*
- O: may miss plausible replies
- T: catches wrong tool order
- S: catches invalid ticket state when encoded
- F: combines trace and state

## F02: Wrong line or customer id in tool args / mutations

### T43

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | yes | no |
| S | yes | yes | no |
| T | yes | yes | no |
| F | yes | yes | no |

### T46

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | yes | no |
| S | yes | yes | no |
| T | yes | no | yes |
| F | yes | no | yes |

*Design intent (not measured):*
- T: wrong args in trace
- S: wrong line mutation in store

## F03: Unsupported credit / policy-violating compensation

### T22

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | yes | no |
| S | no | yes | — |
| T | no | no | — |
| F | no | no | — |

### T27

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | no | yes |
| S | yes | yes | no |
| T | yes | yes | no |
| F | yes | yes | no |

*Design intent (not measured):*
- S: invalid credit rows
- T: trace shows apply_bill_credit after ineligible specialist

## F04: Authentication bypass / privacy leak

### T45

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | yes | no |
| S | yes | yes | no |
| T | yes | yes | no |
| F | yes | yes | no |

### T50

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | yes | no |
| S | yes | yes | no |
| T | yes | yes | no |
| F | yes | yes | no |

*Design intent (not measured):*
- T: sensitive read before auth
- O: output reveals details

## F05: Nested specialist child tool order / structure

### T40

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | yes | no |
| S | yes | yes | no |
| T | no | no | — |
| F | no | no | — |

### T38

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | yes | no |
| S | yes | yes | no |
| T | yes | no | yes |
| F | yes | no | yes |

*Design intent (not measured):*
- T: nested trace order and children

## F06: Conditional structured specialist output violations

### T09

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | yes | no |
| S | yes | yes | no |
| T | no | no | — |
| F | no | no | — |

### T23

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | no | yes |
| S | yes | no | yes |
| T | no | no | — |
| F | no | no | — |

### T10

| Oracle | Eligible | Fault pass | Detected |
|--------|----------|------------|----------|
| O | yes | yes | no |
| S | yes | no | yes |
| T | no | no | — |
| F | no | no | — |

*Design intent (not measured):*
- T: m.object matchers on specialist result
- O: LLM rubric on explanation
