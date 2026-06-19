# agent-spec-kit — Presentation speaker plan & transcript

**Total budget: 18 minutes, INCLUDING the demo.** Plan: **~9 min slides +
~8 min demo + buffer**. The demo sits between Part I (the library) and Part II
(the evaluation), so the audience sees the tool work before hearing the numbers.

> This is a fast deck (26 slides). Aim ~25–35 s per content slide. Land *one* idea
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
| 5 | …and you can't script every conversation | 0:30 | 2:25 |
| 6 | Research question | 0:25 | 2:50 |
| 7 | — *Part I divider* | 0:05 | 2:55 |
| 8 | Core idea: scenario = conversation script | 0:50 | 3:45 |
| 9 | Matcher language — matching the reply | 0:35 | 4:20 |
| 10 | Matching the tool trace *(optional)* | 0:25 | 4:45 |
| 11 | …and the matchers compose *(optional)* | 0:25 | 5:10 |
| 12 | Precise diagnostics: counterexamples | 0:40 | 5:50 |
| 13 | Framework-neutral execution model | 0:25 | 6:15 |
| 14 | Authored tests → automatic discovery | 0:30 | 6:45 |
| 15 | Persistent runs, CLI, web UI | 0:25 | 7:10 |
| 16 | — *Live Demo divider* → **DEMO** | ~8 min | ~15:10 |
| 17 | — *Part II divider* | 0:05 | 15:15 |
| 18 | TelcoSupportBench testbed | 0:35 | 15:50 |
| 19 | Finding 1 — output-only insufficient | 0:40 | 16:30 |
| 20 | Finding 2 — more expressive, less code | 0:30 | 17:00 |
| 21 | Finding 3 — full oracles catch faults | 0:25 | 17:25 |
| 22 | Finding 4 — generative discovery | 0:35 | 18:00 |
| 23 | Threats to validity *(optional)* | 0:20 | 18:20 |
| 24 | Conclusion | 0:30 | 18:50 |
| 25 | Future work *(optional)* | 0:15 | 19:05 |
| 26 | Thank you / questions | — | — |

> Running ~1 min over with everything in. **Claw-back levers (marked *optional*):**
> - **Slides 10 & 11** (tool-trace + compose): the reply matcher on slide 9 already
>   makes the point. Show 9, then *flick* through 10–11 in ~15 s total, or skip.
> - **Slide 23 (threats)** and **slide 25 (future work)**: fold into the closing
>   sentence / Q&A.
>
> Priority if you overrun: protect the **demo** and **Findings 1 & 4** (the
> "well-motivated + promising" core). Slide 5 sets up the generative half, so the
> demo's discovery step and Finding 4 land — keep it. A live pre-auth bug
> (analogous to the report's T45 finding) is **shown live in the demo**, not on a
> slide.

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

### 5 — …and you can't script every conversation (0:30)
"And there's a second gap. Hand-written scenarios capture the policies you
*already* know — the cases you thought of. But agents are stochastic and real
users are messy: they rephrase, omit details, push back, change their mind
mid-conversation. The failures that bite are the dialogue paths nobody scripted.
So a test framework should also do two things: **explore** conversations
automatically — simulated users and transcript fuzzing — and when exploration
finds a real failure, **keep it** as a permanent regression test."

### 6 — Research question (0:25)
"So: can we evaluate stateful, tool-using agents in a **software-testing style** —
readable scenarios combining assertions over replies, tool trajectories, and
state, while keeping enough evidence to diagnose failures precisely? The answer is
agent-spec-kit."

### 7 — Part I divider (0:05)
"First, the library."

### 8 — Core idea (0:50)  *(key slide)*
"The central idea: a scenario **is** a conversation script with the contract woven
in. The user sends a message; `assert_output` checks the reply — that's **O**;
`assert_tool_calls` checks the agent authenticated *before* touching account tools
— that's **T**, the trace; and `assert_that` runs a database postcondition — **S**,
state. All three surfaces in one file that reads like the dialogue, instead of
being scattered across datasets, graders, and runner config. Note `assert_that`
just takes the function — the `store` fixture is injected by name."

### 9 — Matcher language: the reply (0:35)
"Checks are one composable matcher language. Literals, dicts, lists are
auto-coerced. Combine them — here `one_of` of two `contains` for alternate
phrasings. And where text genuinely needs judgement, drop in an **LLM rubric** —
but as pass/fail criteria, not an opaque score."

### 10 — Matching the tool trace (0:25)  *(optional)*
"The same language matches the normalised **tool trace**. Order and extras are
explicit: `ordered=True` pins the sequence, `allow_extras=True` lets other calls
interleave, and `forbid_tool_calls` asserts a tool is *never* used."

### 11 — …and the matchers compose (0:25)  *(optional)*
"And it composes into structure: `m.object` constrains only the fields you name,
`m.list` does ordered or unordered, and **conditional rules** require or forbid a
field only *when* another holds — e.g. a pager group is required only for
high-severity incidents."

### 12 — Precise diagnostics (0:40)  *(key slide)*
"Diagnostics are the other half of the value. A scalar tells you *that* it failed;
a **counterexample** tells you *where*. Every failed assertion names the check, a
human location like 'after turn 2', and a **JSON-pointer path** to the exact
mismatch — `$[1].args.line_id`, expected vs. actual. Same view in the terminal,
the store, and the web UI."

### 13 — Framework-neutral execution (0:25)
"Architecturally: fixtures and scenarios → CLI runs them → `materialise` drives
the agent turn by turn → matchers check each turn; pass persists, fail emits a
counterexample. Adapters for LangChain and Pydantic AI **normalise traces**, so
oracles never depend on a framework's message format."

### 14 — Authored tests → discovery (0:30)
"Authored scenarios encode what you know. To find what you *don't*, the same
oracles power **user simulation** and **mutation fuzzing** to generate new
dialogues, **shrinking** reduces a failure to a minimal reproducer, and
**extraction** pins it back as a permanent regression — one loop, discovery to
regression."

### 15 — Persistence, CLI, web UI (0:25)
"Every run is stored locally with git metadata. A CLI — `run`, `runs`, `show`,
`ui` — and a read-only web browser: runs list, trace drawer, fuzz trials, and a
compare view across experiments. Let me show you all of this live."

---

## 🔴 SLIDE 16 — LIVE DEMO (~8 min) — outline

> Goal: let the audience *see* the Part I pillars working end-to-end —
> authoring, precise failure, generative discovery, the UI. All code is in
> **`demo/`** (see `demo/README.md`); a mini mobile-support agent driving the
> exact same story as the slides.
>
> **Pre-flight (before the talk):**
> - `cd agent_spec_kit`; `set -a; . ./.env; set +a` (loads `OPENAI_API_KEY`).
>   Web UI already running in a browser tab: `uv run agent-spec-kit ui --open`.
> - Editor open on `demo/test_demo.py` + `demo/test_discovery.py`; big terminal
>   font; scrollback cleared; `rm -f demo/regressions/test_extracted.py`.
> - **Pre-run all three commands once** under `--experiment demo` so the UI has
>   rows for step 3 and imports are warm (the first run builds the package).
> - Each run is **~4–7 s live** (`gpt-5-nano`, `reasoning_effort=low`; the 5 fuzz
>   trials run concurrently). Offline (`unset OPENAI_API_KEY`) is instant and
>   deterministic — the identical pass/fail story, your safety net if the network
>   misbehaves.

**Flow principle — run first, talk over it; never type-then-stare.** Because a
live run is a few seconds, **kick the command off, then immediately turn to the
code and narrate** — the result lands while you're talking, and you read it out.
The command is punctuation, not a pause.

1. **Author + run, then walk the code (≈1.5 min).** Type & launch:
   `uv run agent-spec-kit run demo/ --tags demo-pass --experiment demo`.
   *While it runs*, scroll `test_billing_credit`: "user message… the reply check —
   O… authenticate-before-billing — T… a state postcondition — S." By now it's
   back → "green: all three surfaces held."

2. **Make it fail precisely (≈2 min).** Launch:
   `uv run agent-spec-kit run demo/ --tags demo-fail --experiment demo`. *While it
   runs*, point at the `LINE-001` line: "the customer actually asked about
   LINE-002 — watch what the failure tells us." Read the box: "not just *failed* —
   the trace check, after turn 2, at path `$[1].args.line_id`, expected
   `LINE-001`, got `LINE-002`." (Tie to the *Precise diagnostics* slide.)

3. **Browse results in the web UI (≈2 min).** *All clicking + talking — no command
   waiting.* Browser tab → runs list → open the failing run → scenario table →
   **trace drawer** on the failing repeat: same failure card + the nested event
   tree (agent turn → authenticate → get_line_status). One sentence on **compare**.

4. **Generative discovery (≈2 min).** Launch:
   `uv run agent-spec-kit run demo/ --tags demo-discovery --extract --experiment demo`.
   *While it runs*, set it up: "the script only tests what I thought of — let the
   fuzzer vary the opening: customers who *claim* they're already verified." Read
   the result: "every trial withheld a real token, but the agent trusted them,
   fabricated a token, and read the account — calling billing/line tools with no
   verification. A bug I never scripted." Then
   `cat demo/regressions/test_extracted.py`: "`--extract` pinned it as a permanent
   regression." (No `--shrink` — skipped for speed.)

5. **One-line wrap (≈30 s).** "Author, fail precisely, discover, pin as a
   regression — one model. Now, does it pay off?" → advance to Part II.

> **Risk management:** verified live on `gpt-5-nano` — step 1 passes (6/6), step 2
> fails at `$[1].args.line_id`, step 4 finds the access-without-verification bug
> (4/4) and extracts a regression that reproduces it. If a live run stalls > ~15 s
> (occasional API spike), keep talking through the code; or `unset
> OPENAI_API_KEY` and re-run — offline is instant and identical.

---

### 17 — Part II divider (0:05)
"Does multi-surface, scenario-driven testing actually pay off?"

### 18 — TelcoSupportBench (0:35)
"To evaluate it I built TelcoSupportBench — a synthetic mobile-support domain: 50
tasks against a reference LangGraph agent (coordinator + two specialists). Each
task has four oracle lanes — output, trace, state, and full. Tools stay
*permissive*; **policy is asserted in the oracles**, not hidden in the simulator.
Compared against seven other approaches."

### 19 — Finding 1 (0:40)  *(key slide)*
"First finding: output-only grading is not enough. Across 200 oracle slots, **all
50 output lanes passed** — yet **54 slots failed**, every one in the trace, state,
or full lanes. The reply sounded right while a tool ran out of order or a store
update never happened. Output-only would have reported a clean 100%."

### 20 — Finding 2 (0:30)
"Second: more expressive, less code. Across twelve canonical check patterns,
agent-spec-kit needed **165 lines** vs 496 (DeepEval) and 532 (Pydantic Evals) —
and the **highest clarity grade on every specimen**, giving an exact path witness
where others return a scalar or bare AssertionError."

### 21 — Finding 3 (0:25)
"Third: full oracles catch faults narrow lanes miss. Ten injected fault families —
output detection is often **zero** for tool-ordering and state faults, while state
and full lanes hit **75–100%**. The combined oracle beats any single surface."

### 22 — Finding 4 (0:35)  *(key slide)*
"Fourth: generative testing finds bugs nobody scripted. From 14 manual scripts,
simulation and fuzzing reached far more tool paths and **many more distinct
failure signatures** — 24 and 18 vs 3 — same oracle, then shrunk and extracted to
regressions. You saw exactly this in the demo: the agent reading account data
without proper verification."

### 23 — Threats to validity (0:20)  *(optional)*
"Honest limits: clarity grades used LLM judges, not a human study; one agent, one
domain whose design may favour the framework; and fewer than half of extracted
scenarios reproduced the *exact* signature on immediate rerun. Promising, but this
setup — not agents in general."

### 24 — Conclusion (0:30)
"The right unit of evaluation is the **behavioural episode**, not the final reply.
agent-spec-kit unifies output, trace, and state in one readable, framework-neutral
scenario, with assertion-local diagnostics and a discovery-to-regression workflow
— evidenced by hidden failures exposed, 3× less check code, and real bugs found."

### 25 — Future work (0:15)  *(optional)*
"Future: more domains and frameworks, human studies of clarity, signature-stable
replay after extraction, larger team-based suites."

### 26 — Thank you (Q&A)
"Thank you — happy to take questions."

---

## Figures: status

**Self-built TikZ / native visuals (no external image):**
- Slide 2 — agent → fluent reply (✓) while trace & state silently fail (✗).
- Slide 3 — three O/T/S surface cards.
- Slide 5 — "conversation space" ellipse: authored scripts cluster vs. scattered
  unscripted failures.
- Slides 8–11 — code listings (scenario + the three matcher slides).
- Slide 12 — abstract "scalar / AssertionError vs. pinpointed counterexample"
  contrast (the *concept*; real errors are shown in the demo).
- Slide 13 — framework-neutral execution diagram.
- Slide 14 — discovery→regression flow.
- Findings 1 & 2 — native `pgfplots` bar charts; Finding 3 — native LaTeX table.
  Edit the numbers directly in the `.tex`.

**Real figures from the report / theme:**
- `langfuse_example_trace.png` (slide 4, existing tools)
- `specific_run_page_ui.png` (slide 15, web UI)
- `tao_bench_setup.png` (slide 18, benchmark inspiration — stand-in)

**Optional improvement:**
- **Slide 18 (TelcoSupportBench)** uses the τ-bench setup image as a stand-in —
  replace with a real TelcoSupportBench architecture diagram (coordinator +
  specialists + tools/DB) if you draw one.
- Extra UI screenshots in `images/` for demo-backup slides if wanted:
  `runs_page_ui.png`, `compare_page_ui.png`, `rich_console_failure_output.png`.

## Build
```bash
cd Ruthvik_FYP_presentation
xelatex presentation.tex   # run twice (pgfplots); XeLaTeX required for fonts
```
