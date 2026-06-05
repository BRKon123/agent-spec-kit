# Fuzzing Study

- Generated: 2026-05-31T15:18:29.146883+00:00
- Run id: 20260531T145454Z
- Tasks: T03, T04, T17, T20, T27, T29, T30, T35, T38, T42, T43, T44, T45, T49
- Calibration steering: False

## Primary comparison

| Method | Tasks | Conversations | Unique tool paths | Distinct failure signatures | Median turns | Authoring |
|--------|------:|--------------:|------------------:|----------------------------:|-------------:|-----------|
| Manual scripts | 14 | 14 | 10 | 3 | 4.0 | Manual script (canonical seed) |
| User simulation | 14 | 70 | 58 | 24 | 4.0 | Task profile + persona seed |
| Mutation fuzz | 14 | 70 | 36 | 18 | 6.0 | Manual seed + mutation operator |

## Operator-level fuzz failures

- `minimise_user_replies`: 4 failing conversations
- `delay_required_fact`: 3 failing conversations
- `ambiguous_acknowledgement`: 3 failing conversations
- `drop_required_fact`: 3 failing conversations
- `increase_pressure`: 3 failing conversations
- `repeat_or_reorder_turn`: 2 failing conversations
- `third_party_shift`: 2 failing conversations
- `swap_entity`: 1 failing conversations
- `contradict_entity_later`: 1 failing conversations
- `negate_completed_step`: 1 failing conversations
- `remove_confirmation`: 1 failing conversations
- `interleave_secondary_intent`: 1 failing conversations

## Claim

Fuzzing applies generic mutation operators over valid manual-script user turns and reuses the same F-oracle as user simulation. It tests whether small transcript perturbations surface tool-path and failure-signature diversity beyond manual scripts and persona-based simulation.

