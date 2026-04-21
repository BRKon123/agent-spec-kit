"""Multi-turn LangGraph scenario: SQLite + JSON tools with queued checks (no explicit materialise).

The scenario body only queues steps; :func:`run_scenario_job` calls :meth:`Scenario.materialise`
when the body returns. After each user message, ``assert_tool_calls`` and ``assert_that`` inspect
the last model turn and the on-disk stores.

Intentionally failing scenarios use the ``expected-failure`` tag (see ``uv run agent-spec-kit run …
--tags expected-failure``).
"""

from __future__ import annotations

import json

import agent_spec_kit as ek
import agent_spec_kit.match as m


def _after_first_turn(store) -> None:
    conn = store.connect()
    try:
        cur = conn.execute("SELECT qty FROM items WHERE sku = ?", ("demo-sku",))
        row = cur.fetchone()
        assert row is not None, "expected demo-sku row in SQLite"
        assert int(row[0]) == 4, f"expected qty 4, got {row[0]!r}"

        cur = conn.execute(
            "SELECT COUNT(*) FROM events WHERE event_type = ? AND detail LIKE ?",
            ("receive", "%demo%"),
        )
        assert cur.fetchone()[0] >= 1, "expected audit row for receive"
    finally:
        conn.close()

    blob = json.loads(store.json_path.read_text(encoding="utf-8"))
    assert blob.get("last_sku") == "demo-sku"
    assert blob.get("ops", {}).get("restocked") is True


def _after_second_turn(store) -> None:
    conn = store.connect()
    try:
        cur = conn.execute("SELECT COALESCE(SUM(qty), 0) FROM items")
        total = int(cur.fetchone()[0])
    finally:
        conn.close()

    blob = json.loads(store.json_path.read_text(encoding="utf-8"))
    rollup = blob.get("rollup", {})
    assert rollup.get("units") == total, (
        f"JSON rollup.units should mirror SQL sum of qty (got {rollup.get('units')!r} vs sql {total})"
    )


def _after_second_turn_env_gate_only(second_turn_env_gate_ok: bool) -> None:
    """Fixture-driven gate that fails when the second turn's ``assert_that`` runs."""
    assert second_turn_env_gate_ok, (
        "second-turn env gate not satisfied (example: missing deploy flag / CI secret)"
    )


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("langchain", "example", "sql-json", "smoke"),
    timeout_s=180.0,
)
async def test_sql_json_multi_turn_tool_and_env_checks(s, store):
    """Two user turns; tool expectations (unordered) and direct SQLite/JSON assertions."""
    (
        s.user_message(
            "You control inventory and a JSON sidecar file via tools only; keep the final reply short.\n"
            "1) Call inventory_upsert with sku \"demo-sku\", label \"Assorted bolts\", quantity 4.\n"
            "2) Call audit_log with event_type \"receive\" and detail \"demo restock batch\".\n"
            "3) Call json_patch_merge with patch_json string: "
            "{\"last_sku\":\"demo-sku\",\"ops\":{\"restocked\":true}}\n"
            "4) End with one sentence listing the sku you stored."
        )
        .assert_tool_calls(
            [
                m.tool_call("inventory_upsert"),
                m.tool_call("audit_log"),
                m.tool_call("json_patch_merge"),
            ],
            ordered=False,
            allow_extras=True,
        )
        .assert_that(_after_first_turn)
        .user_message(
            "1) Call inventory_select_sql with this exact query string: "
            "SELECT sku, qty FROM items ORDER BY sku\n"
            "2) Call inventory_summary.\n"
            "3) Call json_path_set with dotted_key \"rollup.units\" and value_json set to the JSON "
            "number (no quotes) equal to total_units from inventory_summary.\n"
            "4) Reply with a single line echoing total_units from inventory_summary."
        )
        .assert_tool_calls(
            [
                m.tool_call("inventory_select_sql"),
                m.tool_call("inventory_summary"),
                m.tool_call("json_path_set"),
            ],
            ordered=False,
            allow_extras=True,
        )
        .assert_that(_after_second_turn)
        .assert_output(m.contains("4"))
    )


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("langchain", "example", "sql-json", "expected-failure"),
    timeout_s=180.0,
)
async def test_sql_json_fail_tool_calls_wrong_args_after_second_user_message(s, store):
    """Turn 1 matches the smoke test; turn 2 *prompts* wrong tool arguments.

    Expectations still require the contract from the passing scenario (correct SQL query and
    rollup ``value_json``). The model follows the misleading turn-2 instructions, so three tools
    are still called but ``assert_tool_calls`` fails with argument mismatch diagnostics.
    """
    _want_query = "SELECT sku, qty FROM items ORDER BY sku"
    _want_rollup_json = "4"
    (
        s.user_message(
            "You control inventory and a JSON sidecar file via tools only; keep the final reply short.\n"
            "1) Call inventory_upsert with sku \"demo-sku\", label \"Assorted bolts\", quantity 4.\n"
            "2) Call audit_log with event_type \"receive\" and detail \"demo restock batch\".\n"
            "3) Call json_patch_merge with patch_json string: "
            "{\"last_sku\":\"demo-sku\",\"ops\":{\"restocked\":true}}\n"
            "4) End with one sentence listing the sku you stored."
        )
        .assert_tool_calls(
            [
                m.tool_call("inventory_upsert"),
                m.tool_call("audit_log"),
                m.tool_call("json_patch_merge"),
            ],
            ordered=False,
            allow_extras=True,
        )
        .assert_that(_after_first_turn)
        .user_message(
            "Data is already in SQLite and JSON from the prior message. Follow these steps "
            "exactly as written — do not substitute a better query or rollup value:\n"
            "1) Call inventory_select_sql with query string exactly: SELECT COUNT(*) AS n FROM items\n"
            "2) Call inventory_summary with no arguments.\n"
            "3) Call json_path_set with dotted_key \"rollup.units\" and value_json \"99\" "
            "(digits only, meaning ninety-nine).\n"
            "4) Reply with one short line."
        )
        .assert_tool_calls(
            [
                m.tool_call("inventory_select_sql", args={"query": _want_query}),
                m.tool_call("inventory_summary"),
                m.tool_call(
                    "json_path_set",
                    args={"dotted_key": "rollup.units", "value_json": _want_rollup_json},
                ),
            ],
            ordered=False,
            allow_extras=True,
        )
    )


@ek.scenario(
    agent_fixture="adapted_agent",
    repeats=1,
    tags=("langchain", "example", "sql-json", "expected-failure"),
    timeout_s=180.0,
)
async def test_sql_json_fail_env_assert_after_second_user_message(s, store, second_turn_env_gate_ok):
    """Same complexity as the smoke test; ``assert_that`` fails after turn 2 (fixture env gate)."""
    (
        s.user_message(
            "You control inventory and a JSON sidecar file via tools only; keep the final reply short.\n"
            "1) Call inventory_upsert with sku \"demo-sku\", label \"Assorted bolts\", quantity 4.\n"
            "2) Call audit_log with event_type \"receive\" and detail \"demo restock batch\".\n"
            "3) Call json_patch_merge with patch_json string: "
            "{\"last_sku\":\"demo-sku\",\"ops\":{\"restocked\":true}}\n"
            "4) End with one sentence listing the sku you stored."
        )
        .assert_tool_calls(
            [
                m.tool_call("inventory_upsert"),
                m.tool_call("audit_log"),
                m.tool_call("json_patch_merge"),
            ],
            ordered=False,
            allow_extras=True,
        )
        .assert_that(_after_first_turn)
        .user_message(
            "1) Call inventory_select_sql with this exact query string: "
            "SELECT sku, qty FROM items ORDER BY sku\n"
            "2) Call inventory_summary.\n"
            "3) Call json_path_set with dotted_key \"rollup.units\" and value_json set to the JSON "
            "number (no quotes) equal to total_units from inventory_summary.\n"
            "4) Reply with a single line echoing total_units from inventory_summary."
        )
        .assert_tool_calls(
            [
                m.tool_call("inventory_select_sql"),
                m.tool_call("inventory_summary"),
                m.tool_call("json_path_set"),
            ],
            ordered=False,
            allow_extras=True,
        )
        .assert_that(_after_second_turn_env_gate_only)
    )
