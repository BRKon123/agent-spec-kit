"""Local SQLite-backed result storage and blob helpers."""

from __future__ import annotations

import gzip
import json
import sqlite3
import statistics
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from typing import cast

from agent_spec_kit.storage_records import (
    AssertionResultRecord,
    RepeatResultRecord,
    RunRecord,
    RunSummary,
    ScenarioResultRecord,
    Status,
    StorageConfig,
)


def write_json_blob(path: Path, value: Any) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, default=str)
    return str(path)


def read_json_blob(path: Path) -> Any:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


class LocalResultStore:
    def __init__(self, config: StorageConfig) -> None:
        self._config = config
        self._root = config.root
        self._sqlite_path = config.sqlite_path or (self._root / "results.sqlite")
        self._blobs_root = self._root / "blobs"
        self._root.mkdir(parents=True, exist_ok=True)
        self._blobs_root.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @property
    def sqlite_path(self) -> Path:
        return self._sqlite_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._sqlite_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        schema = """
        CREATE TABLE IF NOT EXISTS experiments (
            experiment_id TEXT PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            experiment_id TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            status TEXT NOT NULL,
            command TEXT,
            notes TEXT,
            git_commit TEXT,
            git_branch TEXT,
            git_dirty INTEGER,
            python_version TEXT,
            package_version TEXT,
            metadata_json TEXT NOT NULL,
            summary_json TEXT,
            FOREIGN KEY (experiment_id) REFERENCES experiments(experiment_id)
        );
        CREATE TABLE IF NOT EXISTS scenario_results (
            scenario_result_id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            scenario_name TEXT NOT NULL,
            scenario_module TEXT,
            scenario_file TEXT,
            scenario_key TEXT NOT NULL,
            parameter_key TEXT NOT NULL,
            parameters_json TEXT NOT NULL,
            tags_json TEXT NOT NULL,
            status TEXT NOT NULL,
            repeats_total INTEGER NOT NULL,
            repeats_passed INTEGER NOT NULL,
            repeats_failed INTEGER NOT NULL,
            duration_ms INTEGER,
            summary_json TEXT NOT NULL,
            FOREIGN KEY (run_id) REFERENCES runs(run_id)
        );
        CREATE TABLE IF NOT EXISTS repeat_results (
            repeat_result_id TEXT PRIMARY KEY,
            scenario_result_id TEXT NOT NULL,
            repeat_index INTEGER NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            duration_ms INTEGER,
            output_preview TEXT,
            failure_kind TEXT,
            failure_message TEXT,
            events_blob_path TEXT,
            transcript_blob_path TEXT,
            assertions_blob_path TEXT,
            counterexample_blob_path TEXT,
            raw_error_blob_path TEXT,
            FOREIGN KEY (scenario_result_id) REFERENCES scenario_results(scenario_result_id)
        );
        CREATE TABLE IF NOT EXISTS assertions (
            assertion_id TEXT PRIMARY KEY,
            repeat_result_id TEXT NOT NULL,
            assertion_type TEXT NOT NULL,
            actor TEXT,
            turn_index INTEGER,
            status TEXT NOT NULL,
            message TEXT,
            details_json TEXT NOT NULL,
            counterexample_blob_path TEXT,
            FOREIGN KEY (repeat_result_id) REFERENCES repeat_results(repeat_result_id)
        );
        CREATE INDEX IF NOT EXISTS idx_runs_experiment ON runs(experiment_id);
        CREATE INDEX IF NOT EXISTS idx_scenario_run ON scenario_results(run_id);
        CREATE INDEX IF NOT EXISTS idx_scenario_key ON scenario_results(scenario_key);
        CREATE INDEX IF NOT EXISTS idx_repeat_scenario ON repeat_results(scenario_result_id);
        CREATE INDEX IF NOT EXISTS idx_repeat_status ON repeat_results(status);
        CREATE INDEX IF NOT EXISTS idx_assertion_status ON assertions(status);
        """
        with self._connect() as conn:
            conn.executescript(schema)
            conn.commit()

    def _ensure_experiment(self, conn: sqlite3.Connection, run: RunRecord) -> None:
        conn.execute(
            """
            INSERT INTO experiments (experiment_id, name, description, created_at, metadata_json)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(name) DO NOTHING
            """,
            (run.experiment_id, run.experiment_name, None, run.started_at, "{}"),
        )
        row = conn.execute(
            "SELECT experiment_id FROM experiments WHERE name = ?",
            (run.experiment_name,),
        ).fetchone()
        if row is None:
            msg = f"failed to resolve experiment {run.experiment_name!r}"
            raise RuntimeError(msg)
        if row["experiment_id"] != run.experiment_id:
            conn.execute(
                "UPDATE experiments SET experiment_id = ? WHERE name = ?",
                (run.experiment_id, run.experiment_name),
            )

    def create_run(self, run: RunRecord) -> None:
        with self._connect() as conn:
            self._ensure_experiment(conn, run)
            conn.execute(
                """
                INSERT INTO runs (
                    run_id, experiment_id, started_at, finished_at, status, command, notes,
                    git_commit, git_branch, git_dirty, python_version, package_version,
                    metadata_json, summary_json
                ) VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    run.run_id,
                    run.experiment_id,
                    run.started_at,
                    run.status,
                    run.command,
                    run.notes,
                    run.git_commit,
                    run.git_branch,
                    None if run.git_dirty is None else int(run.git_dirty),
                    run.python_version,
                    run.package_version,
                    json.dumps(run.metadata, default=str),
                ),
            )
            conn.commit()

    def save_scenario_result(self, result: ScenarioResultRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO scenario_results (
                    scenario_result_id, run_id, scenario_name, scenario_module, scenario_file,
                    scenario_key, parameter_key, parameters_json, tags_json, status,
                    repeats_total, repeats_passed, repeats_failed, duration_ms, summary_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(scenario_result_id) DO UPDATE SET
                    status=excluded.status,
                    repeats_passed=excluded.repeats_passed,
                    repeats_failed=excluded.repeats_failed,
                    duration_ms=excluded.duration_ms,
                    summary_json=excluded.summary_json
                """,
                (
                    result.scenario_result_id,
                    result.run_id,
                    result.scenario_name,
                    result.scenario_module,
                    result.scenario_file,
                    result.scenario_key,
                    result.parameter_key,
                    json.dumps(result.parameters, default=str),
                    json.dumps(list(result.tags), default=str),
                    result.status,
                    result.repeats_total,
                    result.repeats_passed,
                    result.repeats_failed,
                    result.duration_ms,
                    json.dumps(result.summary, default=str),
                ),
            )
            conn.commit()

    def save_repeat_result(self, result: RepeatResultRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO repeat_results (
                    repeat_result_id, scenario_result_id, repeat_index, status, started_at, finished_at,
                    duration_ms, output_preview, failure_kind, failure_message, events_blob_path,
                    transcript_blob_path, assertions_blob_path, counterexample_blob_path, raw_error_blob_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(repeat_result_id) DO UPDATE SET
                    status=excluded.status,
                    finished_at=excluded.finished_at,
                    duration_ms=excluded.duration_ms,
                    output_preview=excluded.output_preview,
                    failure_kind=excluded.failure_kind,
                    failure_message=excluded.failure_message,
                    events_blob_path=excluded.events_blob_path,
                    transcript_blob_path=excluded.transcript_blob_path,
                    assertions_blob_path=excluded.assertions_blob_path,
                    counterexample_blob_path=excluded.counterexample_blob_path,
                    raw_error_blob_path=excluded.raw_error_blob_path
                """,
                (
                    result.repeat_result_id,
                    result.scenario_result_id,
                    result.repeat_index,
                    result.status,
                    result.started_at,
                    result.finished_at,
                    result.duration_ms,
                    result.output_preview,
                    result.failure_kind,
                    result.failure_message,
                    result.events_blob_path,
                    result.transcript_blob_path,
                    result.assertions_blob_path,
                    result.counterexample_blob_path,
                    result.raw_error_blob_path,
                ),
            )
            conn.commit()

    def save_assertion_result(self, result: AssertionResultRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO assertions (
                    assertion_id, repeat_result_id, assertion_type, actor, turn_index, status,
                    message, details_json, counterexample_blob_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(assertion_id) DO UPDATE SET
                    status=excluded.status,
                    message=excluded.message,
                    details_json=excluded.details_json,
                    counterexample_blob_path=excluded.counterexample_blob_path
                """,
                (
                    result.assertion_id,
                    result.repeat_result_id,
                    result.assertion_type,
                    result.actor,
                    result.turn_index,
                    result.status,
                    result.message,
                    json.dumps(result.details, default=str),
                    result.counterexample_blob_path,
                ),
            )
            conn.commit()

    def _percentile(self, values: list[int], p: float) -> int:
        if not values:
            return 0
        s = sorted(values)
        i = int(round((len(s) - 1) * p))
        return s[i]

    def compute_run_summary(self, run_id: str) -> RunSummary:
        with self._connect() as conn:
            scenario_rows = conn.execute(
                "SELECT status, tags_json, parameters_json FROM scenario_results WHERE run_id = ?",
                (run_id,),
            ).fetchall()
            repeat_rows = conn.execute(
                """
                SELECT rr.status, rr.duration_ms, rr.failure_kind, sr.scenario_key, sr.parameters_json
                FROM repeat_results rr
                JOIN scenario_results sr ON sr.scenario_result_id = rr.scenario_result_id
                WHERE sr.run_id = ?
                """,
                (run_id,),
            ).fetchall()

        scenario_count = len(scenario_rows)
        scenario_passed = sum(1 for row in scenario_rows if row["status"] == "passed")
        scenario_failed = sum(1 for row in scenario_rows if row["status"] == "failed")
        scenario_errored = sum(1 for row in scenario_rows if row["status"] == "error")
        scenario_timeout = sum(1 for row in scenario_rows if row["status"] == "timeout")

        repeat_count = len(repeat_rows)
        repeat_passed = sum(1 for row in repeat_rows if row["status"] == "passed")
        repeat_failed = repeat_count - repeat_passed
        repeat_pass_rate = (repeat_passed / repeat_count) if repeat_count else 0.0
        scenario_pass_rate = (scenario_passed / scenario_count) if scenario_count else 0.0

        durations = [int(row["duration_ms"]) for row in repeat_rows if row["duration_ms"] is not None]
        mean_duration_ms = float(statistics.fmean(durations)) if durations else 0.0
        p50_duration_ms = self._percentile(durations, 0.5)
        p95_duration_ms = self._percentile(durations, 0.95)

        failure_kinds_counter: Counter[str] = Counter(
            str(row["failure_kind"]) for row in repeat_rows if row["failure_kind"]
        )
        failure_kinds = dict(failure_kinds_counter)

        by_scenario_status: dict[str, set[str]] = defaultdict(set)
        for row in repeat_rows:
            by_scenario_status[str(row["scenario_key"])].add(str(row["status"]))
        flaky_scenarios = sum(
            1 for statuses in by_scenario_status.values() if "passed" in statuses and len(statuses) > 1
        )

        tag_counter: Counter[str] = Counter()
        for row in scenario_rows:
            for tag in json.loads(row["tags_json"]):
                tag_counter[str(tag)] += 1
        tag_breakdown = dict(tag_counter)

        param_totals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        param_passed: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for row in repeat_rows:
            params = json.loads(row["parameters_json"])
            for key, value in params.items():
                name = str(value)
                param_totals[key][name] += 1
                if row["status"] == "passed":
                    param_passed[key][name] += 1
        parameter_breakdown: dict[str, dict[str, Any]] = {}
        for key, values in param_totals.items():
            parameter_breakdown[key] = {}
            for value, total in values.items():
                passed = param_passed[key].get(value, 0)
                parameter_breakdown[key][value] = {
                    "repeat_count": total,
                    "repeat_passed": passed,
                    "repeat_pass_rate": (passed / total) if total else 0.0,
                }

        status = "passed"
        if scenario_timeout > 0:
            status = "timeout"
        elif scenario_errored > 0:
            status = "error"
        elif scenario_failed > 0:
            status = "failed"

        return RunSummary(
            status=cast(Status, status),
            scenario_count=scenario_count,
            scenario_passed=scenario_passed,
            scenario_failed=scenario_failed,
            scenario_errored=scenario_errored,
            scenario_timeout=scenario_timeout,
            repeat_count=repeat_count,
            repeat_passed=repeat_passed,
            repeat_failed=repeat_failed,
            repeat_pass_rate=repeat_pass_rate,
            scenario_pass_rate=scenario_pass_rate,
            flaky_scenarios=flaky_scenarios,
            mean_duration_ms=mean_duration_ms,
            p50_duration_ms=p50_duration_ms,
            p95_duration_ms=p95_duration_ms,
            failure_kinds=failure_kinds,
            tag_breakdown=tag_breakdown,
            parameter_breakdown=parameter_breakdown,
        )

    def finish_run(self, run_id: str, summary: RunSummary) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE runs
                SET status = ?, finished_at = ?, summary_json = ?
                WHERE run_id = ?
                """,
                (summary.status, utc_now_iso(), json.dumps(summary.as_json(), default=str), run_id),
            )
            conn.commit()

    def list_runs(
        self,
        *,
        limit: int = 20,
        offset: int = 0,
        experiment_id: str | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if experiment_id is not None:
            clauses.append("r.experiment_id = ?")
            params.append(experiment_id)
        if status is not None:
            clauses.append("r.status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"""
            SELECT r.run_id, r.experiment_id, e.name AS experiment_name, r.status,
                   r.started_at, r.finished_at, r.summary_json, r.metadata_json
            FROM runs r
            JOIN experiments e ON e.experiment_id = r.experiment_id
            {where}
            ORDER BY r.started_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        out: list[dict[str, Any]] = []
        for row in rows:
            summary = json.loads(row["summary_json"]) if row["summary_json"] else {}
            out.append(
                {
                    "run_id": row["run_id"],
                    "experiment_id": row["experiment_id"],
                    "experiment_name": row["experiment_name"],
                    "status": row["status"],
                    "started_at": row["started_at"],
                    "finished_at": row["finished_at"],
                    "scenario_passed": summary.get("scenario_passed", 0),
                    "scenario_count": summary.get("scenario_count", 0),
                    "scenario_failed": summary.get("scenario_failed", 0),
                    "repeat_pass_rate": summary.get("repeat_pass_rate", 0.0),
                    "mean_duration_ms": summary.get("mean_duration_ms", 0.0),
                    "summary": summary,
                    "metadata": json.loads(row["metadata_json"]) if row["metadata_json"] else {},
                }
            )
        return out

    def list_experiments(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT e.experiment_id, e.name, e.created_at,
                       COUNT(r.run_id) AS run_count,
                       MAX(r.started_at) AS last_run_at,
                       (
                           SELECT r2.status FROM runs r2
                           WHERE r2.experiment_id = e.experiment_id
                           ORDER BY r2.started_at DESC LIMIT 1
                       ) AS last_run_status,
                       (
                           SELECT r2.run_id FROM runs r2
                           WHERE r2.experiment_id = e.experiment_id
                           ORDER BY r2.started_at DESC LIMIT 1
                       ) AS last_run_id
                FROM experiments e
                LEFT JOIN runs r ON r.experiment_id = e.experiment_id
                GROUP BY e.experiment_id
                ORDER BY last_run_at DESC NULLS LAST, e.name ASC
                """
            ).fetchall()
        return [
            {
                "experiment_id": row["experiment_id"],
                "name": row["name"],
                "created_at": row["created_at"],
                "run_count": row["run_count"],
                "last_run_at": row["last_run_at"],
                "last_run_status": row["last_run_status"],
                "last_run_id": row["last_run_id"],
            }
            for row in rows
        ]

    def list_scenarios_for_run(self, run_id: str) -> list[dict[str, Any]]:
        """Return all scenarios for a run, each with its repeats inlined."""
        with self._connect() as conn:
            scenario_rows = conn.execute(
                """
                SELECT scenario_result_id, run_id, scenario_name, scenario_module, scenario_file,
                       scenario_key, parameter_key, parameters_json, tags_json, status,
                       repeats_total, repeats_passed, repeats_failed, duration_ms, summary_json
                FROM scenario_results
                WHERE run_id = ?
                ORDER BY scenario_module, scenario_name, parameter_key
                """,
                (run_id,),
            ).fetchall()
            repeat_rows = conn.execute(
                """
                SELECT rr.repeat_result_id, rr.scenario_result_id, rr.repeat_index,
                       rr.status, rr.started_at, rr.finished_at, rr.duration_ms,
                       rr.output_preview, rr.failure_kind, rr.failure_message,
                       (SELECT COUNT(*) FROM assertions a WHERE a.repeat_result_id = rr.repeat_result_id)
                           AS assertion_count,
                       (SELECT COUNT(*) FROM assertions a WHERE a.repeat_result_id = rr.repeat_result_id
                            AND a.status = 'passed') AS assertion_passed
                FROM repeat_results rr
                JOIN scenario_results sr ON sr.scenario_result_id = rr.scenario_result_id
                WHERE sr.run_id = ?
                ORDER BY rr.scenario_result_id, rr.repeat_index
                """,
                (run_id,),
            ).fetchall()

        repeats_by_scenario: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in repeat_rows:
            repeats_by_scenario[row["scenario_result_id"]].append(
                {
                    "repeat_result_id": row["repeat_result_id"],
                    "repeat_index": row["repeat_index"],
                    "status": row["status"],
                    "started_at": row["started_at"],
                    "finished_at": row["finished_at"],
                    "duration_ms": row["duration_ms"],
                    "output_preview": row["output_preview"],
                    "failure_kind": row["failure_kind"],
                    "failure_message": row["failure_message"],
                    "assertion_count": row["assertion_count"],
                    "assertion_passed": row["assertion_passed"],
                }
            )

        out: list[dict[str, Any]] = []
        for row in scenario_rows:
            out.append(
                {
                    "scenario_result_id": row["scenario_result_id"],
                    "run_id": row["run_id"],
                    "scenario_name": row["scenario_name"],
                    "scenario_module": row["scenario_module"],
                    "scenario_file": row["scenario_file"],
                    "scenario_key": row["scenario_key"],
                    "parameter_key": row["parameter_key"],
                    "parameters": json.loads(row["parameters_json"]) if row["parameters_json"] else {},
                    "tags": json.loads(row["tags_json"]) if row["tags_json"] else [],
                    "status": row["status"],
                    "repeats_total": row["repeats_total"],
                    "repeats_passed": row["repeats_passed"],
                    "repeats_failed": row["repeats_failed"],
                    "duration_ms": row["duration_ms"],
                    "summary": json.loads(row["summary_json"]) if row["summary_json"] else {},
                    "repeats": repeats_by_scenario.get(row["scenario_result_id"], []),
                }
            )
        return out

    def get_repeat(self, repeat_result_id: str) -> dict[str, Any] | None:
        """Return the repeat row plus its scenario context and blob paths, or None."""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT rr.*, sr.scenario_name, sr.scenario_module, sr.scenario_key,
                       sr.parameter_key, sr.parameters_json, sr.tags_json, sr.run_id
                FROM repeat_results rr
                JOIN scenario_results sr ON sr.scenario_result_id = rr.scenario_result_id
                WHERE rr.repeat_result_id = ?
                """,
                (repeat_result_id,),
            ).fetchone()
            if row is None:
                return None
            assertions = conn.execute(
                """
                SELECT assertion_id, assertion_type, actor, turn_index, status, message,
                       details_json, counterexample_blob_path
                FROM assertions WHERE repeat_result_id = ?
                ORDER BY assertion_id
                """,
                (repeat_result_id,),
            ).fetchall()
        return {
            "repeat_result_id": row["repeat_result_id"],
            "scenario_result_id": row["scenario_result_id"],
            "run_id": row["run_id"],
            "scenario_name": row["scenario_name"],
            "scenario_module": row["scenario_module"],
            "scenario_key": row["scenario_key"],
            "parameter_key": row["parameter_key"],
            "parameters": json.loads(row["parameters_json"]) if row["parameters_json"] else {},
            "tags": json.loads(row["tags_json"]) if row["tags_json"] else [],
            "repeat_index": row["repeat_index"],
            "status": row["status"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "duration_ms": row["duration_ms"],
            "output_preview": row["output_preview"],
            "failure_kind": row["failure_kind"],
            "failure_message": row["failure_message"],
            "events_blob_path": row["events_blob_path"],
            "transcript_blob_path": row["transcript_blob_path"],
            "assertions_blob_path": row["assertions_blob_path"],
            "counterexample_blob_path": row["counterexample_blob_path"],
            "raw_error_blob_path": row["raw_error_blob_path"],
            "assertions": [
                {
                    "assertion_id": a["assertion_id"],
                    "assertion_type": a["assertion_type"],
                    "actor": a["actor"],
                    "turn_index": a["turn_index"],
                    "status": a["status"],
                    "message": a["message"],
                    "details": json.loads(a["details_json"]) if a["details_json"] else {},
                    "counterexample_blob_path": a["counterexample_blob_path"],
                }
                for a in assertions
            ],
        }

    def compare_experiments_most_recent(
        self, experiment_ids: list[str]
    ) -> dict[str, Any]:
        """
        Pivot view across N experiments. For each experiment, pick its latest run.
        Then for every (scenario_key, parameter_key) seen in any of those runs,
        pick the latest repeat from that run as the cell value.
        Missing cells are None.
        """
        if not experiment_ids:
            return {"experiments": [], "rows": []}

        with self._connect() as conn:
            placeholders = ",".join("?" for _ in experiment_ids)
            exp_rows = conn.execute(
                f"""
                SELECT e.experiment_id, e.name,
                       (SELECT r.run_id FROM runs r
                         WHERE r.experiment_id = e.experiment_id
                         ORDER BY r.started_at DESC LIMIT 1) AS latest_run_id,
                       (SELECT r.started_at FROM runs r
                         WHERE r.experiment_id = e.experiment_id
                         ORDER BY r.started_at DESC LIMIT 1) AS latest_run_started_at
                FROM experiments e
                WHERE e.experiment_id IN ({placeholders})
                """,
                experiment_ids,
            ).fetchall()
            exp_meta = {
                row["experiment_id"]: {
                    "experiment_id": row["experiment_id"],
                    "name": row["name"],
                    "latest_run_id": row["latest_run_id"],
                    "latest_run_started_at": row["latest_run_started_at"],
                }
                for row in exp_rows
            }

            run_ids = [m["latest_run_id"] for m in exp_meta.values() if m["latest_run_id"]]
            if not run_ids:
                ordered = [exp_meta[eid] for eid in experiment_ids if eid in exp_meta]
                return {"experiments": ordered, "rows": []}

            run_placeholders = ",".join("?" for _ in run_ids)
            scenario_rows = conn.execute(
                f"""
                SELECT sr.scenario_result_id, sr.run_id, sr.scenario_name, sr.scenario_key,
                       sr.parameter_key, sr.parameters_json, sr.tags_json, sr.status AS scenario_status,
                       sr.duration_ms AS scenario_duration_ms,
                       sr.repeats_passed, sr.repeats_failed, sr.repeats_total,
                       r.experiment_id
                FROM scenario_results sr
                JOIN runs r ON r.run_id = sr.run_id
                WHERE sr.run_id IN ({run_placeholders})
                """,
                run_ids,
            ).fetchall()
            latest_repeat_rows = conn.execute(
                f"""
                SELECT rr.scenario_result_id, rr.repeat_result_id, rr.repeat_index,
                       rr.status, rr.duration_ms, rr.failure_kind, rr.failure_message
                FROM repeat_results rr
                JOIN scenario_results sr ON sr.scenario_result_id = rr.scenario_result_id
                WHERE sr.run_id IN ({run_placeholders})
                  AND rr.repeat_index = (
                      SELECT MAX(rr2.repeat_index) FROM repeat_results rr2
                      WHERE rr2.scenario_result_id = rr.scenario_result_id
                  )
                """,
                run_ids,
            ).fetchall()

        latest_repeat_by_scenario_id: dict[str, dict[str, Any]] = {
            row["scenario_result_id"]: {
                "repeat_result_id": row["repeat_result_id"],
                "repeat_index": row["repeat_index"],
                "status": row["status"],
                "duration_ms": row["duration_ms"],
                "failure_kind": row["failure_kind"],
                "failure_message": row["failure_message"],
            }
            for row in latest_repeat_rows
        }

        # row_key -> { display, cells: { exp_id -> cell or None } }
        rows_by_key: dict[tuple[str, str], dict[str, Any]] = {}
        for row in scenario_rows:
            row_key = (row["scenario_key"], row["parameter_key"])
            if row_key not in rows_by_key:
                rows_by_key[row_key] = {
                    "scenario_key": row["scenario_key"],
                    "parameter_key": row["parameter_key"],
                    "scenario_name": row["scenario_name"],
                    "parameters": json.loads(row["parameters_json"]) if row["parameters_json"] else {},
                    "tags": json.loads(row["tags_json"]) if row["tags_json"] else [],
                    "cells": {eid: None for eid in exp_meta},
                }
            latest_repeat = latest_repeat_by_scenario_id.get(row["scenario_result_id"])
            cell: dict[str, Any] = {
                "scenario_result_id": row["scenario_result_id"],
                "run_id": row["run_id"],
                "scenario_status": row["scenario_status"],
                "scenario_duration_ms": row["scenario_duration_ms"],
                "repeats_passed": row["repeats_passed"],
                "repeats_failed": row["repeats_failed"],
                "repeats_total": row["repeats_total"],
                "latest_repeat": latest_repeat,
            }
            rows_by_key[row_key]["cells"][row["experiment_id"]] = cell

        ordered_experiments = [exp_meta[eid] for eid in experiment_ids if eid in exp_meta]
        ordered_rows = sorted(rows_by_key.values(), key=lambda r: (r["scenario_key"], r["parameter_key"]))
        return {"experiments": ordered_experiments, "rows": ordered_rows}

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT r.*, e.name AS experiment_name
                FROM runs r
                JOIN experiments e ON e.experiment_id = r.experiment_id
                WHERE r.run_id = ?
                """,
                (run_id,),
            ).fetchone()
            if row is None:
                return None
            failures = conn.execute(
                """
                SELECT sr.scenario_key, rr.failure_message
                FROM repeat_results rr
                JOIN scenario_results sr ON sr.scenario_result_id = rr.scenario_result_id
                WHERE sr.run_id = ? AND rr.status != 'passed'
                ORDER BY sr.scenario_key, rr.repeat_index
                """,
                (run_id,),
            ).fetchall()
        return {
            "run_id": row["run_id"],
            "experiment_name": row["experiment_name"],
            "status": row["status"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "notes": row["notes"],
            "summary": json.loads(row["summary_json"]) if row["summary_json"] else {},
            "metadata": json.loads(row["metadata_json"]) if row["metadata_json"] else {},
            "failures": [
                {"scenario_key": f["scenario_key"], "failure_message": f["failure_message"]}
                for f in failures
            ],
        }

