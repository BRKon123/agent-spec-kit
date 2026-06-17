# agent-spec-kit — Presentation speaker plan & transcript

**Total budget: 18 minutes, INCLUDING the demo.** Plan: **~9 min slides +
~8 min demo + buffer**. The demo sits between Part I (the library) and Part II
(the evaluation), so the audience sees the tool work before hearing the numbers.

> This is a fast deck (25 slides). Aim ~25–35 s per content slide. Land *one* idea
> per slide and move on — the detail is in the report, not the talk. The four
> section dividers are each one spoken sentence.

Slides compiled from `presentation.tex` (XeLaTeX, Imperial beamer theme).
Slide numbers below are **physical PDF pages**.

| # | Slide | Target | Running |
|---|-------|-------:|--------:|
| 1 | Title | 0:15 | 0:15 |
| 2 | Tool-using agents act on the world | 0:35 | 0:50 |
| 3 | Correctness lives on three surfaces (O/T/S) | 0:30 | 1:20 |
| 4 | Existing tools cover part of the loop | 0:35 | 1:55 |
| 5 | Research question | 0:25 | 2:20 |
| 6 | — *Part I divider* | 0:05 | 2:25 |
| 7 | Core idea: scenario = conversation script | 0:50 | 3:15 |
| 8 | Matcher language — matching the reply | 0:35 | 3:50 |
| 9 | Matching the tool trace *(optional)* | 0:25 | 4:15 |
| 10 | …and the matchers compose *(optional)* | 0:25 | 4:40 |
| 11 | Precise diagnostics: counterexamples | 0:40 | 5:20 |
| 12 | Framework-neutral execution model | 0:25 | 5:45 |
| 13 | Authored tests → automatic discovery | 0:30 | 6:15 |
| 14 | Persistent runs, CLI, web UI | 0:25 | 6:40 |
| 15 | — *Live Demo divider* → **DEMO** | ~8 min | ~14:40 |
| 16 | — *Part II divider* | 0:05 | 14:45 |
| 17 | TelcoSupportBench testbed | 0:35 | 15:20 |
| 18 | Finding 1 — output-only insufficient | 0:40 | 16:00 |
| 19 | Finding 2 — more expressive, less code | 0:30 | 16:30 |
| 20 | Finding 3 — full oracles catch faults | 0:25 | 16:55 |
| 21 | Finding 4 — generative discovery | 0:35 | 17:30 |
| 22 | Honest about the limits *(optional)* | 0:20 | 17:50 |
| 23 | Conclusion | 0:30 | 18:20 |
| 24 | Future work *(optional)* | 0:15 | 18:35 |
| 25 | Thank you / questions | — | — |

> Running ~0:30 over with everything in. **Claw-back levers (marked *optional*):**
> - **Slides 9 & 10** (tool-trace + compose): the reply matcher on slide 8 already
>   makes the point. Show 8, then *flick* through 9–10 in ~15 s total, or skip.
> - **Slide 22 (threats)** and **slide 24 (future work)**: fold into the closing
>   sentence / Q&A.
>
> Priority if you overrun: protect the **demo** and **Findings 1 & 4** (the
> "well-motivated + promising" core). The T45 privacy bug is **shown live in the
> demo**, not on a slide.

---

## Transcript (talking points per slide)

### 1 — Title (0:15)
"Good morning. I'm Ruthvik — my project is *agent-spec-kit*: a framework for
**scenario-driven evaluation and testing of tool-using LLM agents**. I'll motivate
the problem, show you the library with a live demo, then the evaluation evidence."

### 2 — Tool-using agents act on the world (0:35)
"LLMs have moved from text generators to **agents** that plan, call tools, and
**change external state**. Once an agent can act, correctness can't be judged from
the final reply alone. A support agent can sound perfectly polite while it skips
authentication, calls the wrong tool, or leaves the database invalid — the reply
passes, the actions and state silently don't."

### 3 — Correctness lives on three surfaces (0:30)
"Correctness spans three surfaces: **Output** — what it says; **Trace** — which
tools it called and in what order; **State** — what it left behind. A failure on
any one can be hidden by a fluent reply, even masked by recovery on a later turn.
So we must assert over all three, across a whole conversation."

### 4 — Existing tools cover part of the loop (0:35)
"Existing tools each cover part of this. Output graders / LLM-judges — HELM,
G-Eval — compare final answers but are blind to tool and state failures. Agent
benchmarks like τ-bench and AppWorld are trace/state aware but fixed leaderboards,
not infrastructure for *your* agent. Trace viewers like Langfuse show *what*
happened — you still infer what *should* have. **The gap:** no reusable way to
assert over output + trace + state in one scenario with precise diagnostics."

### 5 — Research question (0:25)
"So: can we evaluate stateful, tool-using agents in a **software-testing style** —
readable scenarios combining assertions over replies, tool trajectories, and
state, while keeping enough evidence to diagnose failures precisely? The answer is
agent-spec-kit."

### 6 — Part I divider (0:05)
"First, the library."

### 7 — Core idea (0:50)  *(key slide)*
"The central idea: a scenario **is** a conversation script with the contract woven
in. The user sends a message; `assert_output` checks the reply — that's **O**;
`assert_tool_calls` checks the agent authenticated *before* touching account tools
— that's **T**, the trace; and `assert_that` runs a database postcondition — **S**,
state. All three surfaces in one file that reads like the dialogue, instead of
being scattered across datasets, graders, and runner config. Note `assert_that`
just takes the function — the `store` fixture is injected by name."

### 8 — Matcher language: the reply (0:35)
"Checks are one composable matcher language. Literals, dicts, lists are
auto-coerced. Combine them — here `one_of` of two `contains` for alternate
phrasings. And where text genuinely needs judgement, drop in an **LLM rubric** —
but as pass/fail criteria, not an opaque score."

### 9 — Matching the tool trace (0:25)  *(optional)*
"The same language matches the normalised **tool trace**. Order and extras are
explicit: `ordered=True` pins the sequence, `allow_extras=True` lets other calls
interleave, and `forbid_tool_calls` asserts a tool is *never* used."

### 10 — …and the matchers compose (0:25)  *(optional)*
"And it composes into structure: `m.object` constrains only the fields you name,
`m.list` does ordered or unordered, and **conditional rules** require or forbid a
field only *when* another holds — e.g. a pager group is required only for
high-severity incidents."

### 11 — Precise diagnostics (0:40)  *(key slide)*
"Diagnostics are the other half of the value. A scalar tells you *that* it failed;
a **counterexample** tells you *where*. Every failed assertion names the check, a
human location like 'after turn 2', and a **JSON-pointer path** to the exact
mismatch — `$[1].args.line_id`, expected vs. actual. Same view in the terminal,
the store, and the web UI."

### 12 — Framework-neutral execution (0:25)
"Architecturally: fixtures and scenarios → CLI runs them → `materialise` drives
the agent turn by turn → matchers check each turn; pass persists, fail emits a
counterexample. Adapters for LangChain and Pydantic AI **normalise traces**, so
oracles never depend on a framework's message format."

### 13 — Authored tests → discovery (0:30)
"Authored scenarios encode what you know. To find what you *don't*, the same
oracles power **user simulation** and **mutation fuzzing** to generate new
dialogues, **shrinking** reduces a failure to a minimal reproducer, and
**extraction** pins it back as a permanent regression — one loop, discovery to
regression."

### 14 — Persistence, CLI, web UI (0:25)
"Every run is stored locally with git metadata. A CLI — `run`, `runs`, `show`,
`ui` — and a read-only web browser: runs list, trace drawer, fuzz trials, and a
compare view across experiments. Let me show you all of this live."

---

## 🔴 SLIDE 15 — LIVE DEMO (~8 min) — outline

> Goal: let the audience *see* the Part I pillars working end-to-end on the real
> benchmark — authoring, precise failure, generative discovery, the UI. Terminal
> (large font) + a browser tab on the web UI, both pre-warmed.
>
> **Pre-flight (before the talk):**
> - `cd agent_spec_kit`, virtualenv active, `OPENAI_API_KEY` set.
> - Pre-run a clean baseline so results exist instantly:
>   `agent-spec-kit run benchmarks/telecom_support/ --tags pilot,reference`
> - Web UI already running: `agent-spec-kit ui --open`.
> - Saved T45 fuzz transcript open as a fallback (live fuzzing is slow/stochastic).
> - Increase terminal font; clear scrollback; `clear` between segments.

**[GAP — fill in exact commands once rehearsed; rough script below.]**

1. **Author a scenario (≈2 min).** Open a scenario (a telecom task or
   `examples/langchain_scenario_tests/`). Walk `user_message` → `assert_output` /
   `assert_tool_calls` / `assert_that`; emphasise it reads like the dialogue.
   Run `agent-spec-kit run <path>` → green pass.

2. **Make it fail precisely (≈2 min).** Tighten one assertion (a specific `line_id`,
   or `forbid_tool_calls` a pre-auth tool). Re-run → the **Rich counterexample**:
   failed check, turn, JSON-pointer path. The slide-11 promise, live.

3. **Browse results in the web UI (≈2 min).** Switch to the browser. Runs list →
   open the run → scenario/repeat table → **trace drawer** on the failing repeat:
   same failure card + nested event tree (agent turn → tool calls). Mention
   experiment **compare**.

4. **Generative discovery (≈2 min).** Run a fuzz/sim scenario:
   `agent-spec-kit run <fuzz path> --shrink --extract`. Show the fuzz-trials panel,
   a discovered failure signature absent from the manual script, then the
   **extracted regression `.py`**. *This is where you show the real T45 `CUST-045`
   pre-auth privacy bug* (from the live run, or narrate the saved transcript).

5. **One-line wrap (≈30 s).** "So: author, fail precisely, discover, pin as a
   regression — one model. Now, does it pay off?" → advance to Part II.

> **Demo risk management:** LLM calls are stochastic/networked. Baseline and fuzz
> runs are pre-executed; if anything stalls, fall back to the populated UI and the
> saved transcripts. Never debug live > ~20 s — narrate the pre-run artefacts.

---

### 16 — Part II divider (0:05)
"Does multi-surface, scenario-driven testing actually pay off?"

### 17 — TelcoSupportBench (0:35)
"To evaluate it I built TelcoSupportBench — a synthetic mobile-support domain: 50
tasks against a reference LangGraph agent (coordinator + two specialists). Each
task has four oracle lanes — output, trace, state, and full. Tools stay
*permissive*; **policy is asserted in the oracles**, not hidden in the simulator.
Compared against seven other approaches."

### 18 — Finding 1 (0:40)  *(key slide)*
"First finding: output-only grading is not enough. Across 200 oracle slots, **all
50 output lanes passed** — yet **54 slots failed**, every one in the trace, state,
or full lanes. The reply sounded right while a tool ran out of order or a store
update never happened. Output-only would have reported a clean 100%."

### 19 — Finding 2 (0:30)
"Second: more expressive, less code. Across twelve canonical check patterns,
agent-spec-kit needed **165 lines** vs 496 (DeepEval) and 532 (Pydantic Evals) —
and the **highest clarity grade on every specimen**, giving an exact path witness
where others return a scalar or bare AssertionError."

### 20 — Finding 3 (0:25)
"Third: full oracles catch faults narrow lanes miss. Ten injected fault families —
output detection is often **zero** for tool-ordering and state faults, while state
and full lanes hit **75–100%**. The combined oracle beats any single surface."

### 21 — Finding 4 (0:35)  *(key slide)*
"Fourth: generative testing finds bugs nobody scripted. From 14 manual scripts,
simulation and fuzzing reached far more tool paths and **many more distinct
failure signatures** — 24 and 18 vs 3 — same oracle, then shrunk and extracted to
regressions. You saw exactly this in the demo: the pre-auth privacy bug."

### 22 — Threats to validity (0:20)  *(optional)*
"Honest limits: clarity grades used LLM judges, not a human study; one agent, one
domain whose design may favour the framework; and fewer than half of extracted
scenarios reproduced the *exact* signature on immediate rerun. Promising, but this
setup — not agents in general."

### 23 — Conclusion (0:30)
"The right unit of evaluation is the **behavioural episode**, not the final reply.
agent-spec-kit unifies output, trace, and state in one readable, framework-neutral
scenario, with assertion-local diagnostics and a discovery-to-regression workflow
— evidenced by hidden failures exposed, 3× less check code, and real bugs found."

### 24 — Future work (0:15)  *(optional)*
"Future: more domains and frameworks, human studies of clarity, signature-stable
replay after extraction, larger team-based suites."

### 25 — Thank you (Q&A)
"Thank you — happy to take questions."

---

## Figures: status

**Self-built TikZ / native visuals (no external image):**
- Slide 2 — agent → fluent reply (✓) while trace & state silently fail (✗).
- Slide 3 — three O/T/S surface cards.
- Slides 7–10 — code listings (scenario + the three matcher slides).
- Slide 11 — abstract "scalar / AssertionError vs. pinpointed counterexample"
  contrast (the *concept*; real errors are shown in the demo).
- Slide 12 — framework-neutral execution diagram.
- Slide 13 — discovery→regression flow.
- Findings 1 & 2 — native `pgfplots` bar charts; Finding 3 — native LaTeX table.
  Edit the numbers directly in the `.tex`.

**Real figures from the report / theme:**
- `langfuse_example_trace.png` (slide 4, existing tools)
- `specific_run_page_ui.png` (slide 14, web UI)
- `tao_bench_setup.png` (slide 17, benchmark inspiration — stand-in)

**Optional improvement:**
- **Slide 17 (TelcoSupportBench)** uses the τ-bench setup image as a stand-in —
  replace with a real TelcoSupportBench architecture diagram (coordinator +
  specialists + tools/DB) if you draw one.
- Extra UI screenshots in `images/` for demo-backup slides if wanted:
  `runs_page_ui.png`, `compare_page_ui.png`, `rich_console_failure_output.png`.

## Build
```bash
cd Ruthvik_FYP_presentation
xelatex presentation.tex   # run twice (pgfplots); XeLaTeX required for fonts
```
