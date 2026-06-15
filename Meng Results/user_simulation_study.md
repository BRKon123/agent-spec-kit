# User Simulation Study

- Generated: 2026-05-28T17:39:46.756561+00:00
- Tasks: T04, T17, T20, T27, T29, T30, T35, T38, T42, T43, T45, T49, T03, T44

## Primary table

| Method | Tasks | Conversations | Unique tool paths | Distinct simulation-discovered failure signatures | Median turns | Authoring effort |
|--------|------:|--------------:|------------------:|--------------------------------------------------:|-------------:|------------------|
| Manual scripts | 14 | 14 | 12 | 0 | 4.0 | Manual script text for every conversation |
| Simulated users | 14 | 70 | 60 | 30 | 4.0 | One profile per task + seeds |

## Fairness table

| Comparison | Method | Tasks | Conversations | Unique tool paths | Distinct failure signatures | Authoring effort |
|------------|--------|------:|--------------:|------------------:|----------------------------:|------------------|
| Equal authored artefacts | Manual scripts | 14 | 14 | 12 | 4 | Manual script text for every conversation |
| Equal authored artefacts | Sim users | 14 | 70 | 60 | 30 | One profile per task + seeds |
| Equal conversation count | Manual scripts | 14 | 14 | 12 | 4 | Manual script text for every conversation |
| Equal conversation count | Sim users (first seed only) | 14 | 14 | 14 | 8 | One profile per task + seeds |

## Failure split

- Existing baseline failure: 2
- Simulation-discovered failure: 35
- Invalid simulation: 0

## Transcript snippets

- Manual example: `T04` / `test_t04_manual_study` / `default`
- Manual path: `authenticate_customer -> run_line_diagnostic -> heartbeat_ping -> authenticate_customer -> record_user_action -> run_line_diagnostic -> create_support_ticket`
- Simulated branch example: `T43` / `test_t43_sim_study` / `llm_model=gpt5nano+persona=seed0_simple_correction`
- Simulated path: `authenticate_customer -> check_outage -> get_line_status -> get_line_status -> run_line_diagnostic -> heartbeat_ping -> send_troubleshooting_step -> record_user_action -> create_support_ticket`

Using the same benchmark tasks and correctness oracles, simulated users produced more diverse tool trajectories and uncovered additional failure signatures with less per-conversation authoring effort, while manual scripts remained useful as stable regression paths.
