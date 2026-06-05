# Fuzzing Study

- Generated: 2026-06-05T11:44:18.715946+00:00
- Run id: 20260605T111127Z
- Tasks: T03, T04, T17, T20, T27, T29, T30, T35, T38, T42, T43, T44, T45, T49
- Mutation backend: llm
- Calibration steering: False

## Primary comparison

| Method | Tasks | Conversations | Unique tool paths | Distinct failure signatures | Median turns | Authoring |
|--------|------:|--------------:|------------------:|----------------------------:|-------------:|-----------|
| Manual scripts | 14 | 14 | 11 | 4 | 4.0 | Manual script (canonical seed) |
| User simulation | 14 | 70 | 56 | 26 | 4.0 | Task profile + persona seed |
| Mutation fuzz | 14 | 70 | 40 | 18 | 4.0 | Manual seed + LLM mutation intents |

## Operator-level fuzz failures

- `minimise_user_replies`: 4 failing conversations
- `ambiguous_acknowledgement`: 4 failing conversations
- `drop_required_fact`: 3 failing conversations
- `delay_required_fact`: 3 failing conversations
- `repeat_or_reorder_turn`: 3 failing conversations
- `increase_pressure`: 3 failing conversations
- `contradict_entity_later`: 2 failing conversations
- `negate_completed_step`: 1 failing conversations
- `remove_confirmation`: 1 failing conversations
- `swap_entity`: 1 failing conversations

## Claim

Fuzzing applies mutation intents over valid manual-script user turns and reuses the same F-oracle as user simulation. In this run, mutations are produced by an LLM rather than deterministic regex/string operators.

