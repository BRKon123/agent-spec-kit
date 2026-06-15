"""Run the live LangGraph reference agent for trace recording."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

_TELECOM = Path(__file__).resolve().parents[2] / "telecom_support"
if str(_TELECOM) not in sys.path:
    sys.path.insert(0, str(_TELECOM))

from agent_wrap import wrap_reference_agent  # noqa: E402
from store.seeds import apply_seed  # noqa: E402
from store.store import TelcoStore  # noqa: E402

from agent_spec_kit.scenario_core import tool_dicts_from_turn_data  # noqa: E402
from agent_spec_kit.run import ConversationTurn  # noqa: E402

from shared.trace_io import save_trace  # noqa: E402


async def run_live_turn(seed_name: str, user_message: str) -> dict[str, Any]:
    base = Path(tempfile.mkdtemp(prefix="expr_bench_"))
    try:
        telco = TelcoStore(base / "telco.sqlite")
        apply_seed(telco, seed_name)
        agent = wrap_reference_agent(telco)
        tr = await agent.run_turn(user_message)
        ct = ConversationTurn.from_turn("agent", tr)
        tools = tool_dicts_from_turn_data(ct)
        return {"output": tr.output, "tools": tools, "store_path": str(base / "telco.sqlite")}
    finally:
        shutil.rmtree(base, ignore_errors=True)


async def record_trace(check_id: str, seed_name: str, user_message: str) -> Path:
    data = await run_live_turn(seed_name, user_message)
    payload = {"output": data["output"], "tools": data["tools"]}
    return save_trace(check_id, payload)
