# User Simulation Study

Hand-authored study scenarios comparing:
- canonical manual scripts (one run per task)
- LLM-powered simulated users (five persona seeds per task)

Scenarios live in `tasks/user_simulation/scenarios/` with one file per task.
Each file defines:
- task intent
- in-file persona table (`seed=0..4`)
- situational facts the sim user knows (canonical IDs and beliefs—not manual turn scripts)
- manual study scenario
- simulation study scenario with `simulate_conversation(...)`

Each segment sets its own `max_turns` cap and should end on task-specific `sim_stop(...)` LLM criteria (`stop_on_actor="agent"`) rather than hitting the cap.

Simulated users decide what to say and when from **goal + persona + situation**; they do not follow scripted `_msg1/_msg2` beats from the manual tests.

Personas use one of two disclosure patterns: `reveal_upfront` or `reveal_when_prompted` (unless Behavior says to withhold a specific fact).

## Commands

```bash
uv run python benchmarks/telecom_support/scripts/run_user_simulation_study.py
uv run python benchmarks/telecom_support/scripts/generate_user_simulation_table.py
```

## Artifacts

- `tasks/user_simulation/user_simulation_study.json`
- `tasks/user_simulation/user_simulation_study.md`
- `tasks/user_simulation/path_signatures.json`
- `tasks/user_simulation/failure_signatures.json`
- `tasks/user_simulation/transcripts/<run_id>/cases/*.json` (per-scenario transcript payloads)
- `tasks/user_simulation/transcripts/<run_id>/agent_traces/*.jsonl` (agent trace logs from `agent_wrap`)
- `tasks/user_simulation/transcripts/<run_id>/logs/run.log` (human-readable progress log)
- `tasks/user_simulation/transcripts/<run_id>/logs/run_events.jsonl` (structured run/case events)
- `tasks/user_simulation/transcripts/<run_id>/run_manifest.json` (full per-run manifest copy)
