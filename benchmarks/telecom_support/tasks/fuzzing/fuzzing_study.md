# Fuzzing Study

- Generated: 2026-05-31T14:50:28.179875+00:00
- Run id: 20260531T140347Z
- Tasks: T03, T04, T17, T20, T27, T29, T30, T35, T38, T42, T43, T44, T45, T49
- Calibration steering: False

## Primary comparison

| Method | Tasks | Conversations | Unique tool paths | Distinct failure signatures | Median turns | Authoring |
|--------|------:|--------------:|------------------:|----------------------------:|-------------:|-----------|
| Manual scripts | 14 | 14 | 13 | 5 | 4.0 | Manual script (canonical seed) |
| User simulation | 14 | 70 | 56 | 27 | 4.0 | Task profile + persona seed |
| Mutation fuzz | 14 | 140 | 39 | 21 | 6.0 | Manual seed + mutation operator |

## Operator-level fuzz failures

- `delay_required_fact`: 8 failing conversations
- `minimise_user_replies`: 8 failing conversations
- `contradict_entity_later`: 6 failing conversations
- `repeat_or_reorder_turn`: 6 failing conversations
- `drop_required_fact`: 6 failing conversations
- `increase_pressure`: 6 failing conversations
- `ambiguous_acknowledgement`: 6 failing conversations
- `swap_entity`: 4 failing conversations
- `remove_confirmation`: 4 failing conversations
- `negate_completed_step`: 2 failing conversations
- `interleave_secondary_intent`: 2 failing conversations

## Claim

Fuzzing applies generic mutation operators over valid manual-script user turns and reuses the same F-oracle as user simulation. It tests whether small transcript perturbations surface tool-path and failure-signature diversity beyond manual scripts and persona-based simulation.

