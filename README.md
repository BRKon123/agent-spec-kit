# agent-spec-kit

Agent specification kit library.

## LangChain / LangGraph

Install the optional stack:

```bash
pip install agent-spec-kit[langchain]
```

**Primary API:** `wrap_langchain_agent` — pass a compiled LangGraph graph (or any runnable with `astream`), an `initial_input_factory` that maps the user message string to the input dict your graph expects, then call `run_turn(user_message)` on the returned `AdaptedAgent`. You get a `TurnResult` with `output`, `events` (typed `ToolCallEvent`, `AgentTurnEvent`, `SubagentCallEvent`), `status`, and `error`.

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
