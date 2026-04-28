# agent-spec-kit

Agent specification kit library.

## Results browser UI

A read-only web UI is available for browsing recorded runs, scenarios, traces,
and comparing experiments side by side.

End-user (the SPA bundle ships in the wheel):

```bash
pip install 'agent-spec-kit[ui]'
agent-spec-kit ui --open      # http://127.0.0.1:8765
```

What's there:

- Runs list with experiment / status filters and a column picker.
- Run detail page: scenarios + repeats table next to a collapsible run side panel
  (summary, git, metadata, failure-kind / tag / parameter breakdowns).
- Trace drawer: nested expandable event tree with per-field toggles for
  ``args`` / ``result`` / ``input`` / ``output`` / ``metadata``, plus a failure
  card mirroring the CLI failure box.
- Compare page: pick **N ≥ 2** experiments (URL: ``/compare?experiments=A,B,C``);
  rows are scenarios, cells repeat per experiment, mismatch rows highlight in
  amber.

### Frontend development (contributors)

The SPA lives in [`frontend/`](frontend/). Built assets land in
``src/agent_spec_kit/web/dist/`` so they're packaged into the wheel.

```bash
# one-shot: build the SPA into src/agent_spec_kit/web/dist/
./scripts/build_ui.sh

# dev loop: backend on :8765, Vite on :5173 with /api proxied
npm --prefix frontend install
uv run agent-spec-kit ui --port 8765 --no-frontend &   # API only
npm --prefix frontend run dev                          # http://localhost:5173
```

CI should run ``./scripts/build_ui.sh --ci`` before ``uv build`` so the
distributed wheel includes the bundle.

## LangChain / LangGraph

Install the optional stack:

```bash
pip install agent-spec-kit[langchain]
```

**Primary API:** `wrap_langchain_agent` — pass a compiled LangGraph graph (or any runnable with `astream`), an `initial_input_factory` that maps the user message string to the input dict your graph expects, then call `run_turn(user_message)` on the returned `AdaptedAgent`. You get a `TurnResult` with `output`, `events` (typically a single root `AgentTurnEvent` whose `children` hold `ToolCallEvent` and nested `AgentTurnEvent` nodes), `status`, and `error`.

- **Stream shape:** use `stream_mode`, `version`, and `subgraphs` on `wrap_langchain_agent` (forwarded to LangGraph `astream`).
- **Runtime data:** use `context` and/or `config` (or callables `str → value` for per-turn values). These are **not** the same as stream options—they correspond to LangGraph `context=` and `RunnableConfig`.

```python
import asyncio
from langchain_core.messages import HumanMessage
from agent_spec_kit import TurnResult
from agent_spec_kit.integrations.langchain_adapter import wrap_langchain_agent

async def main() -> None:
    adapted = wrap_langchain_agent(
        graph,
        lambda msg: {"messages": [HumanMessage(content=msg)]},
        stream_mode="updates",
        version="v2",
    )
    result: TurnResult = await adapted.run_turn("Hello")
    print(result.output, result.events)

asyncio.run(main())
```

## Custom frameworks (CrewAI, etc.)

Implement the `AdaptedAgent` protocol (`async def run_turn(user_message: str) -> TurnResult`) and populate `TurnResult.events` using the typed event classes in `agent_spec_kit.events`. See the module docstring in `agent_spec_kit.run` for a short checklist.

## Async LLM Criteria Checker

Use `agent_spec_kit.match.llm_criteria(...)` to evaluate output against a rubric and pass when at least `threshold` criteria pass.

- `model` uses provider-prefixed routing: `<provider>:<model_name>`, for example `openai:gpt-5-nano` or `anthropic:claude-sonnet-4-5`.
- Prefer pass/fail criteria over broad numeric scoring for more stable judge outputs.
- Use async execution (`await scenario.materialise()` or `await scenario.async_check_output(...)`) when this matcher is involved.

```python
import agent_spec_kit.match as m
from agent_spec_kit import create_scenario

s = create_scenario(agent)
s.user_message("Summarize this incident update for an engineering manager.").assert_output(
    m.llm_criteria(
        criteria=[
            "States the root cause correctly",
            "Mentions customer impact explicitly",
            "Lists concrete next steps",
        ],
        threshold=2,
        model="openai:gpt-5-nano",
    )
)
await s.materialise()
```

You can also inject your own judge backend (sync or async) with `judge_fn(actual, criteria, judge_context)`.

## Live integration tests (OpenAI)

Dev dependencies include `langchain-openai`. Integration tests are marked `integration` and are **excluded by default** (`addopts = -m 'not integration'`).

### Local environment (direnv)

This repo includes [direnv](https://direnv.net/) support so `OPENAI_API_KEY` is set automatically when you enter the project directory.

1. Install direnv and hook it into your shell (see direnv docs for `zsh` / `bash`).
2. Copy `cp .env.example .env` and set `OPENAI_API_KEY` in `.env` (or edit the placeholder in `.env`).
3. From the repo root, run **`direnv allow`** once so direnv trusts `.envrc`.
4. New shells: `cd` into the repo; direnv loads `.env` for that session.

**If you were already `cd`’d into the repo** when you added `.envrc`, direnv may not reload until you change directories (e.g. `cd .. && cd agent_spec_kit`) or run **`eval "$(direnv export zsh)"`** (bash: `eval "$(direnv export bash)"`). After that, `echo $OPENAI_API_KEY` should show your key.

Run integration tests:

```bash
uv run pytest --override-ini addopts= -m integration
```

Manual smoke:

```bash
uv run python examples/langchain_run_turn.py
```

Without direnv, you can still run with a one-off env load: `set -a && source .env && set +a && uv run pytest ...`.
