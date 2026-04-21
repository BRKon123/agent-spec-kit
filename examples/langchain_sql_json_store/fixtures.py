"""LangGraph agent with SQLite + JSON file tools (live OpenAI only).

Requires ``OPENAI_API_KEY`` and the LangChain stack (``dependency-groups`` dev).
The scenario queues multiple user turns with ``assert_tool_calls`` / ``assert_that`` and
relies on the runner's end-of-body ``materialise()`` — no explicit ``await`` in the test.

Run from repo root::

    OPENAI_API_KEY=... uv run agent-spec-kit run examples/langchain_sql_json_store/
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Any

import agent_spec_kit as ek
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from agent_spec_kit.integrations.langchain_adapter import wrap_langchain_agent


def _require_api_key() -> None:
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        raise RuntimeError(
            "langchain_sql_json_store requires OPENAI_API_KEY "
            "(live-only example; install dependency-groups dev and export the key)."
        )


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS items ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "sku TEXT NOT NULL UNIQUE,"
        "label TEXT NOT NULL,"
        "qty INTEGER NOT NULL CHECK (qty >= 0)"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS events ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "event_type TEXT NOT NULL,"
        "detail TEXT NOT NULL"
        ")"
    )
    conn.commit()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, obj: dict[str, Any]) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def _set_dotted(root: dict[str, Any], dotted: str, value: Any) -> None:
    parts = [p for p in dotted.strip().split(".") if p]
    if not parts:
        raise ValueError("empty path")
    cur: Any = root
    for p in parts[:-1]:
        nxt = cur.get(p)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[p] = nxt
        cur = nxt
    cur[parts[-1]] = value


def _get_dotted(root: dict[str, Any], dotted: str) -> Any:
    cur: Any = root
    for p in dotted.split("."):
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


class SqlJsonStore:
    """One SQLite file plus one JSON sidecar, owned by a single scenario run."""

    __slots__ = ("db_path", "json_path")

    def __init__(self, db_path: Path, json_path: Path) -> None:
        self.db_path = db_path
        self.json_path = json_path
        conn = sqlite3.connect(str(db_path))
        try:
            _ensure_schema(conn)
        finally:
            conn.close()
        if not json_path.exists():
            _save_json(json_path, {})

    def connect(self) -> sqlite3.Connection:
        return sqlite3.connect(str(self.db_path))


def make_tools(store: SqlJsonStore) -> list:
    @tool
    def inventory_upsert(sku: str, label: str, quantity: int) -> str:
        """Insert or replace a stock row (unique sku) with a label and non-negative quantity."""
        conn = store.connect()
        try:
            conn.execute(
                "INSERT INTO items (sku, label, qty) VALUES (?,?,?) "
                "ON CONFLICT(sku) DO UPDATE SET label=excluded.label, qty=excluded.qty",
                (sku.strip(), label.strip(), int(quantity)),
            )
            conn.commit()
            return json.dumps({"ok": True, "sku": sku.strip(), "qty": int(quantity)})
        finally:
            conn.close()

    @tool
    def inventory_select_sql(query: str) -> str:
        """Run a single read-only SELECT; rejects anything that does not start with SELECT."""
        q = query.strip()
        if not q.upper().startswith("SELECT"):
            return json.dumps({"error": "only SELECT queries are allowed"})
        conn = store.connect()
        try:
            cur = conn.execute(q)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description] if cur.description else []
            return json.dumps({"columns": cols, "rows": rows})
        except Exception as e:
            return json.dumps({"error": str(e)})
        finally:
            conn.close()

    @tool
    def inventory_summary() -> str:
        """Return sku_count, total_units, and max_qty across all rows (aggregate SQL)."""
        conn = store.connect()
        try:
            cur = conn.execute(
                "SELECT COUNT(*) AS n, COALESCE(SUM(qty),0) AS units, COALESCE(MAX(qty),0) AS hi "
                "FROM items"
            )
            n, units, hi = cur.fetchone()
            return json.dumps({"sku_count": n, "total_units": units, "max_qty": hi})
        finally:
            conn.close()

    @tool
    def audit_log(event_type: str, detail: str) -> str:
        """Append a row to the SQL audit/events table."""
        conn = store.connect()
        try:
            conn.execute(
                "INSERT INTO events (event_type, detail) VALUES (?,?)",
                (event_type.strip(), detail.strip()),
            )
            conn.commit()
            return json.dumps({"ok": True, "event_type": event_type.strip()})
        finally:
            conn.close()

    @tool
    def json_patch_merge(patch_json: str) -> str:
        """Merge a JSON object into the root JSON document (top-level keys overwritten)."""
        patch = json.loads(patch_json)
        if not isinstance(patch, dict):
            return json.dumps({"error": "patch_json must be a JSON object"})
        root = _load_json(store.json_path)
        root.update(patch)
        _save_json(store.json_path, root)
        return json.dumps({"ok": True, "keys": sorted(patch.keys())})

    @tool
    def json_path_set(dotted_key: str, value_json: str) -> str:
        """Set a nested value using dotted keys (e.g. meta.cache.v). value_json is any JSON value."""
        root = _load_json(store.json_path)
        value = json.loads(value_json)
        _set_dotted(root, dotted_key, value)
        _save_json(store.json_path, root)
        return json.dumps({"ok": True, "path": dotted_key})

    @tool
    def json_path_get(dotted_key: str) -> str:
        """Read a nested value; returns JSON {\"path\", \"value\"}."""
        root = _load_json(store.json_path)
        v = _get_dotted(root, dotted_key)
        return json.dumps({"path": dotted_key, "value": v})

    return [
        inventory_upsert,
        inventory_select_sql,
        inventory_summary,
        audit_log,
        json_patch_merge,
        json_path_set,
        json_path_get,
    ]


def _live_graph(tools: list) -> object:
    _require_api_key()
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(model="gpt-5-nano", temperature=0)
    return create_react_agent(llm, tools)


@ek.fixture
async def store():
    base = Path(tempfile.mkdtemp(prefix="ask_sql_json_"))
    try:
        yield SqlJsonStore(base / "inventory.sqlite", base / "sidecar.json")
    finally:
        shutil.rmtree(base, ignore_errors=True)


@ek.fixture
async def adapted_agent(store: SqlJsonStore):
    tools = make_tools(store)
    graph = _live_graph(tools)
    return wrap_langchain_agent(
        graph,
        lambda msg: {"messages": [HumanMessage(content=msg)]},
        stream_mode="updates",
        version="v2",
    )


@ek.fixture
def second_turn_env_gate_ok() -> bool:
    """Always false — paired with ``assert_that`` after turn 2 to simulate a failing env gate."""
    return False
