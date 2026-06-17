# agent-spec-kit — Presentation speaker plan & transcript

**Total budget:** ~28 min = **18 min slides** + **8–10 min live demo**.
Demo sits between Part I (the library) and Part II (the evaluation), so the
audience sees the tool work before hearing the numbers.

Slides compiled from `presentation.tex` (XeLaTeX, Imperial beamer theme).

| # | Slide | Target time | Running |
|---|-------|------------:|--------:|
| 1 | Title | 0:30 | 0:30 |
| 2 | Tool-using agents act on the world | 1:15 | 1:45 |
| 3 | Correctness lives on three surfaces (O/T/S) | 1:00 | 2:45 |
| 4 | Existing tools cover part of the loop | 1:15 | 4:00 |
| 5 | Research question | 0:45 | 4:45 |
| — | **Part I divider** | 0:10 | 4:55 |
| 6 | Core idea: scenario = conversation script | 1:30 | 6:25 |
| 7 | One composable matcher language | 0:50 | 7:15 |
| 8 | Precise diagnostics: counterexamples | 1:10 | 8:25 |
| 9 | Framework-neutral execution model | 0:55 | 9:20 |
| 10 | Discovery → regression workflow | 1:05 | 10:25 |
| 11 | Persistent runs, CLI, web UI | 0:45 | 11:10 |
| — | **DEMO** | 8–10 min | ~20:00 |
| — | **Part II divider** | 0:10 | 20:10 |
| 12 | TelcoSupportBench testbed | 1:10 | 21:20 |
| 13 | Finding 1 — output-only insufficient | 1:05 | 22:25 |
| 14 | Finding 2 — more expressive, less code | 1:00 | 23:25 |
| 15 | Finding 3 — full oracles catch faults | 1:00 | 24:25 |
| 16 | Finding 4 — generative discovery | 1:20 | 25:45 |
| 17 | Threats to validity | 0:45 | 26:30 |
| 18 | Conclusion | 1:00 | 27:30 |
| 19 | Future work | 0:30 | 28:00 |
| 20 | Thank you / questions | — | — |

> If running long, the easiest cuts are slide 7 (matcher language) and slide 17
> (threats can be folded into Q&A). Never cut Findings 1 and 4 — they are the
> "well-motivated + promising" core.

---

## Transcript (talking points per slide)

### 1 — Title (0:30)
"Good morning. I'm Ruthvik, and my project is *agent-spec-kit*: a framework for
**scenario-driven evaluation and testing of tool-using LLM agents**. Over the next
~20 minutes I'll motivate the problem, show you the library — including a live
demo — and then the evaluation evidence that it works."

### 2 — Tool-using agents act on the world (1:15)
"LLMs have moved from text generators to **agents**: they plan, call tools, and
**change external state**. The moment an agent can act, its correctness can no
longer be judged from the final reply alone. A customer-support agent can sound
perfectly polite while it skips authentication and leaks account data, calls the
wrong tool, or leaves the database in an invalid state. The plausible answer is
only *one* part of being correct."

### 3 — Correctness lives on three surfaces (1:00)
"Concretely, correctness spans three surfaces: **Output** — what it says;
**Trace** — which tools it called and in what order; and **State** — what it left
behind in the world. The key problem: a failure on *any* of these can be hidden
by a fluent reply, and even masked by recovery on a later turn. So we need to
assert over all three, across a whole conversation."

### 4 — Existing tools cover part of the loop (1:15)
"Existing tooling each covers part of this. Output graders and LLM-as-judge —
HELM, G-Eval — are great for comparing models on final answers, but blind to tool
and state failures. Agent benchmarks like τ-bench and AppWorld are trace- and
state-aware, but they're fixed leaderboards, not reusable infrastructure for
*your* agent. And trace viewers like Langfuse show you *what* happened — you still
have to infer what *should* have happened. **The gap:** no single reusable way to
assert over output, trace, and state in one multi-turn scenario, with precise
diagnostics when a check fails."

### 5 — Research question (0:45)
"So the question: can we evaluate stateful, tool-using agents in a
**software-testing style** — readable scenarios combining assertions over replies,
tool trajectories, and state, while keeping enough evidence to diagnose failures
precisely? My answer is agent-spec-kit, which I'll now show you."

### 6 — Core idea (1:30)  *(key slide)*
"The central idea: a scenario **is** a conversation script, with the contract
woven in after each turn. Here's a real one. The user sends a message; then
`assert_output` checks the reply — that's **O**. `assert_tool_calls` checks the
agent authenticated *before* touching account tools — that's **T**, the trace.
And `assert_that` runs a postcondition on the database — that's **S**, state. All
three surfaces, in one file that reads like the dialogue itself — instead of being
scattered across datasets, graders, and runner config."

### 7 — Matcher language (0:50)
"Assertions are built from one composable matcher language. Literals, dicts and
lists are auto-coerced into matchers; there are rich combinators for objects,
lists, nested tool calls, and conditional rules. And where you genuinely need
nuance, you can drop in an LLM rubric — but as pass/fail criteria, not an opaque
score."

### 8 — Precise diagnostics (1:10)  *(key slide)*
"Diagnostics are the other half of the value. Every failed assertion produces a
**structured counterexample**: the check that broke, a human-readable location
like 'assert_tool_calls after turn 2', a **JSON-pointer path** to the exact
mismatch — for example `$[1].args.line_id` — and expected-versus-actual. You get
the identical view in the terminal, the stored database, and the web UI. It turns
'it failed somehow' into 'this check broke, here'."

### 9 — Framework-neutral execution (0:55)
"Architecturally: you register fixtures and scenarios; the CLI runs them;
`materialise` drives the agent turn by turn; matchers check each turn. On success
it's persisted; on failure a counterexample is emitted. Crucially, adapters for
LangChain and Pydantic AI **normalise traces** into one event model, so your
oracles never depend on a framework's message format."

### 10 — Discovery → regression (1:05)
"Authored scenarios encode what you already know. To find what you *don't*, the
same oracles power **user simulation** and **mutation fuzzing**, which generate new
dialogues; **shrinking** reduces a failure to a minimal reproducer; and
**extraction** pins it back into the suite as a permanent regression scenario —
one continuous loop from discovery to regression."

### 11 — Persistence, CLI, web UI (0:45)
"Everything is stored locally with git metadata. There's a CLI — `run`, `runs`,
`show`, `ui` — and a read-only web browser with a runs list, a trace drawer, fuzz
trials, and a compare view to track regressions across experiments. Let me show
you all of this live."

---

## 🔴 LIVE DEMO (8–10 minutes) — outline

> Goal: let the audience *see* the four pillars from Part I working end-to-end on
> the real benchmark — authoring, precise failure, generative discovery, and the
> UI. Keep a terminal (large font) and a browser tab on the web UI pre-warmed.
>
> **Pre-flight (before the talk):**
> - `cd agent_spec_kit`, virtualenv active, `OPENAI_API_KEY` set.
> - Pre-run a clean baseline so results exist instantly:
>   `agent-spec-kit run benchmarks/telecom_support/ --tags pilot,reference`
> - Have the web UI already running in a tab: `agent-spec-kit ui --open`.
> - Have the T45 fuzz example handy as a fallback (it's slow/stochastic live).
> - Increase terminal font; clear scrollback; `clear` between segments.

**[GAP — fill in exact commands once rehearsed; rough script below.]**

1. **Author a scenario (≈2 min).**
   Open a scenario file (e.g. a telecom task or `examples/langchain_scenario_tests/`).
   Walk through `user_message` → `assert_output` / `assert_tool_calls` /
   `assert_that`. Emphasise it reads like the dialogue. Run it:
   `agent-spec-kit run <path>` → green pass.

2. **Make it fail precisely (≈2 min).**
   Tighten one assertion (e.g. expect a specific `line_id`, or `forbid_tool_calls`
   a pre-auth tool). Re-run → show the **Rich counterexample** in the terminal:
   the failed check, the turn, and the JSON-pointer path. This is the slide-8
   promise, live.

3. **Browse results in the web UI (≈2 min).**
   Switch to the browser. Runs list → open the run → scenario/repeat table →
   open the **trace drawer** on the failing repeat. Show the same failure card and
   the nested event tree (agent turn → tool calls). Mention experiment **compare**.

4. **Generative discovery (≈2–3 min).**
   Run a fuzz/simulation scenario:
   `agent-spec-kit run <fuzz path> --shrink --extract`.
   Show the fuzz-trials panel, a discovered failure signature absent from the
   manual script, then the **extracted regression `.py`** that was written.
   *(If live fuzzing is too slow/flaky, narrate the pre-run T45 `CUST-045`
   pre-auth privacy bug from the saved transcript instead.)*

5. **One-line wrap (≈30 s).**
   "So: author, fail precisely, discover, and pin as a regression — all in one
   model. Now, does it actually pay off?" → advance to Part II.

> **Demo risk management:** LLM calls are stochastic and networked. The baseline
> and fuzz runs are pre-executed; if anything stalls live, fall back to the
> already-populated UI and the saved transcripts. Never debug live for more than
> ~20s — narrate the pre-run artefacts instead.

---

### 12 — TelcoSupportBench (1:10)
"To evaluate it I built TelcoSupportBench — a synthetic mobile-support domain: 50
tasks against a reference LangGraph agent with a coordinator and two specialists.
Each task has four oracle lanes — output, trace, state, and full. The design
principle is that tools stay *permissive*; **policy is asserted in the oracles**,
not hidden in the simulator. I compared against seven other approaches."

### 13 — Finding 1 (1:05)  *(key slide)*
"First finding: output-only grading is not enough. Across 200 oracle slots, **all
50 output lanes passed** — yet **54 slots failed**, every one in the trace, state,
or full lanes. The reply sounded right while a tool ran out of order or a store
update never happened. Final-answer evaluation alone would have reported a clean
100% pass."

### 14 — Finding 2 (1:00)
"Second: it's more expressive with less code. Across twelve canonical check
patterns, agent-spec-kit needed **165 lines** versus 496 for DeepEval and 532 for
Pydantic Evals — and got the **highest clarity grade on every specimen**. On
failure it gives an exact path witness where the others return a scalar, broad
prose, or a bare AssertionError."

### 15 — Finding 3 (1:00)
"Third: full oracles catch faults the narrow lanes miss. I injected ten fault
families and measured which lane detects each. Output detection is often **zero**
for tool-ordering and state-mutation faults, while state and full lanes hit
**75–100%**. The combined oracle beats any single surface."

### 16 — Finding 4 (1:20)  *(key slide)*
"Fourth: generative testing finds bugs nobody scripted. From 14 manual scripts,
user simulation and fuzzing reached far more tool paths and **many more distinct
failure signatures** — 24 and 18 versus 3 — reusing the same oracle. A concrete
example: a fuzz mutation garbled an opening message but kept the customer id;
the agent then **named and anchored that account in prose before authentication**
— a real pre-auth **privacy** violation the manual script never triggered. And
extraction turns it into a permanent regression test."

### 17 — Threats to validity (0:45)
"I'll be honest about limits: clarity grades used LLM judges, not a human study;
it's one agent and one domain, whose design may favour the framework; and fewer
than half of extracted scenarios reproduced the *exact* signature on immediate
rerun, due to stochastic ordering. The results are promising but describe this
setup, not agents in general."

### 18 — Conclusion (1:00)
"To conclude: the right unit of evaluation is the **behavioural episode**, not the
final reply. agent-spec-kit unifies output, trace, and state oracles in one
readable, framework-neutral scenario, with assertion-local diagnostics, and a
single discovery-to-regression workflow. The evidence: hidden trace/state
failures exposed, three-times-less check code with the best clarity, and
generative testing surfacing real bugs."

### 19 — Future work (0:30)
"Future work: more domains and frameworks, human studies of clarity,
signature-stable replay after extraction, and larger team-based suites."

### 20 — Thank you (Q&A)
"Thank you — happy to take questions."

---

## Figures: status

**Included from the report / theme (real):**
- `react_prompting.png`, `langfuse_example_trace.png` (motivation)
- `rich_console_failure_output.png` (counterexample, slide 8)
- `specific_run_page_ui.png` (web UI, slide 11)
- `tao_bench_setup.png` (benchmark inspiration, slide 12)
- `fuzz_llm_pipeline.png` (fuzzing, slide 16)
- All bar charts (Findings 1 & 2) are native `pgfplots` — edit numbers in `.tex`.
- Detection table (Finding 3) is native LaTeX.

**Placeholders to fill if you have/ want better assets:**
- **Slide 7 (matcher language):** `[FIGURE PLACEHOLDER]` — a clean matcher
  cheat-sheet or nested `m.tool_call` code card. Swap the `\fbox{...}` for an
  `\includegraphics`.
- **Slide 12 (TelcoSupportBench):** currently uses the τ-bench setup image as a
  stand-in — replace with a real TelcoSupportBench architecture diagram
  (coordinator + specialists + tools/DB) if you draw one.
- Other UI screenshots are available in `images/` if you want extra demo-backup
  slides: `runs_page_ui.png`, `compare_page_ui.png`.

## Build
```bash
cd Ruthvik_FYP_presentation
xelatex presentation.tex   # run twice (pgfplots); XeLaTeX required for fonts
```
