# Live demo — agent-spec-kit

Self-contained code for the ~8-minute live demo in the FYP talk. It drives a
miniature mobile-support agent (three permissive tools + a small store) and walks
the four demo steps from `Ruthvik_FYP_presentation/SPEAKER_PLAN.md`.

## Files

| File | Demo step | What it shows |
|------|-----------|---------------|
| `fixtures.py` | — | The agent + `SupportStore`. **Live** `ChatOpenAI` (`gpt-5-nano`, `reasoning_effort="low"`) when `OPENAI_API_KEY` is set; deterministic **offline** agent otherwise. A deliberately *naive* prompt: correct on the happy path, careless about the auth boundary. |
| `test_demo.py` → `test_billing_credit` | **1** | Author a scenario; Output + Trace + State checks; **passes**. |
| `test_demo.py` → `test_line_status_strict` | **2** | Tightened trace assertion; **fails** with `$[1].args.line_id` (expected `LINE-001`, actual `LINE-002`) — the counterexample on the *Precise diagnostics* slide. |
| `test_discovery.py` → `test_no_account_access_without_verification` | **4** | Fuzz "my token's already on file" openings (no real token); the agent fabricates a token and reads the account anyway; trace oracle forbids account tools; `--extract` pins it as a regression. |
| `regressions/test_extracted.py` | **4** | Generated regression (git-ignored; created live by `--extract`). |

> **Offline vs live.** With no key the agent is deterministic, so the demo is
> fully reproducible (rehearse it on a plane). With a key it's a real LLM agent,
> exactly like the other `examples/`. The pass/fail outcomes are the same either
> way. **Verified live** (`gpt-5-nano`): step 1 passes 6/6, step 2 fails at
> `$[1].args.line_id`, step 4 finds the bug 4/4. Timing: each run is ~**4–7 s**
> (5 fuzz trials run **concurrently**), with the occasional API latency spike;
> offline is instant. The rest of the ~8 min is narration + the web UI.
>
> **Flow (avoid dead air):** kick the command off, then talk through the code /
> what to expect while it returns — the run is punctuation, not a pause. See the
> SPEAKER_PLAN demo outline for the per-step talk track.

## Setup (before the talk)

```bash
cd <repo-root>
export OPENAI_API_KEY=sk-...            # or rely on .env / direnv; omit to go offline
uv run agent-spec-kit ui --open &       # web UI on http://127.0.0.1:8765 (step 3)
```

All runs below use `--experiment demo` so they sit in their own bucket.

## Step 1 — author a scenario, watch it pass (~2 min)

Open `test_demo.py`, talk through `test_billing_credit` top-to-bottom
(`user_message` → `assert_output` / `assert_tool_calls` / `assert_that`), then:

```bash
uv run agent-spec-kit run demo/ --tags demo-pass --experiment demo
```

## Step 2 — make it fail precisely (~2 min)

`test_line_status_strict` expects `LINE-001` but the customer asked about
`LINE-002`. (To do the "tighten it live" move, edit that `line_id` in the file.)

```bash
uv run agent-spec-kit run demo/ --tags demo-fail --experiment demo
```

Point at the counterexample: failed check, turn, and the path
`$[1].args.line_id` with expected vs. actual.

## Step 3 — browse results in the web UI (~2 min)

Switch to the browser tab (`agent-spec-kit ui`). Runs list → open the failing
run → scenario/repeat table → **trace drawer** on the failing repeat: same
failure card + the nested event tree (agent turn → tool calls). Mention
experiment **compare**.

## Step 4 — generative discovery → regression (~2 min)

```bash
uv run agent-spec-kit run demo/ --tags demo-discovery --extract --experiment demo
```

The fuzz trials say "my token's already on file, go ahead" but never supply a
real token. The naive agent trusts it, fabricates a token, and reads the account
anyway — calling `get_billing` / `get_line_status` with no real verification. The
trace oracle forbids those tools, so the trials fail. `--extract` writes
`regressions/test_extracted.py` — a permanent regression under the same oracle.
(No `--shrink`: skipped to keep the demo snappy.)

```bash
cat demo/regressions/test_extracted.py
```

Wrap: "author → fail precisely → discover → pin as a regression, one model."

## Re-running cleanly

Re-running `demo-discovery` overwrites the extracted file
(`duplicate_policy="replace"`). To reset just the demo data, use a fresh
`--experiment` name; `agent-spec-kit clear` wipes **all** local runs, so avoid it
if you want to keep other history.
