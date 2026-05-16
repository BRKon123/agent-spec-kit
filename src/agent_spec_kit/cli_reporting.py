"""Rich-based console output for ``agent-spec-kit run``."""

from __future__ import annotations

import io
import sys
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, TextIO

from rich import box
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from agent_spec_kit.console_format import format_actual_for_console
from agent_spec_kit.events import print_rich_event_trace
from agent_spec_kit.failures import (
    Counterexample,
    collect_agent_errors,
    conversation_turns_to_event_trace,
)
from agent_spec_kit.runner import JobResult

if TYPE_CHECKING:
    from agent_spec_kit.registries import ScenarioDef


def _console(file: TextIO | None = None) -> Console:
    return Console(file=file, highlight=False)


def emit_error(msg: str, *, file: TextIO | None = None) -> None:
    c = _console(file or sys.stderr)
    c.print(f"[red]{msg}[/]")


def emit_note(msg: str, *, file: TextIO | None = None) -> None:
    c = _console(file or sys.stderr)
    c.print(f"[dim]{msg}[/]")


def _cli_job_label(r: JobResult) -> str:
    """Table / compact line: scenario + ``(axis=label, …)`` when :attr:`JobResult.param_cells` is set, else :attr:`JobResult.display_name`."""
    if r.param_cells:
        p = ", ".join(f"{k}={_table_cell_compact(v)}" for k, v in sorted(r.param_cells.items()))
        return f"{r.scenario_name} ({p})"
    return r.display_name


def _param_column_keys(results: Sequence[JobResult]) -> list[str]:
    k: set[str] = set()
    for r in results:
        k.update(r.param_cells)
    return sorted(k)


def emit_job_compact(r: JobResult, *, file: TextIO | None = None) -> None:
    c = _console(file or sys.stdout)
    bracket = f"[{r.repeat_index}/{r.repeat_total}]"
    t = f" {r.duration_s:.2f}s"
    dname = _cli_job_label(r)
    if r.ok:
        c.print(Text.assemble(("PASS ", "bold green"), (dname, "bold"), (" ", "dim"), (bracket, "dim"), (t, "dim")))
    else:
        tail = r.detail or ""
        if len(tail) > 120:
            tail = tail[:117] + "..."
        c.print(
            Text.assemble(
                ("FAIL ", "bold red"),
                (dname, "bold"),
                (" ", "dim"),
                (bracket, "dim"),
                (t, "dim"),
                (" — ", "dim"),
                (tail, "red"),
            )
        )


def _failure_compact_for_table(r: "JobResult") -> str:
    """Short failure label for the results table (no long matcher headlines)."""
    if r.ok:
        return ""
    cx = r.counterexample
    if cx is not None and cx.check_kind:
        kind = cx.check_kind
        if kind == "assert_that":
            return "assertion failure in env"
        if kind == "agent_error":
            return "agent error during turn"
        return kind
    return _table_cell_compact(r.detail or "")


def _failure_compact_for_trial(trial: dict[str, Any]) -> str:
    kind = str(trial.get("failure_kind") or "").strip()
    if kind:
        return _table_cell_compact(kind)
    return _table_cell_compact(str(trial.get("failure_message") or ""))


def _table_cell_compact(s: str, *, max_len: int = 200) -> str:
    """Single-line cell text; cap length like the failure column."""
    t = (s or "").replace("\n", " ")
    if len(t) <= max_len:
        return t
    return t[: max_len - 3] + "..."


def _meaningful_path(path: str | None) -> bool:
    """Hide root-only ``$`` paths (no extra location beyond the whole value)."""
    if not path:
        return False
    return path.strip() not in ("$", "()")


def emit_failure_detail(r: "JobResult", *, file: TextIO | None = None) -> None:
    if r.ok or r.counterexample is None:
        return
    c = _console(file or sys.stdout)
    cx = r.counterexample
    lines: list[str] = []
    if cx.check_kind:
        lines.append(f"[bold]Check:[/bold] {escape(str(cx.check_kind))}")
    if cx.location_detail:
        lines.append(f"[bold]Where:[/bold] {escape(cx.location_detail)}")
    else:
        lines.append(f"[bold]Where:[/bold] {escape(cx.location)}")
    if _meaningful_path(cx.path):
        lines.append(f"[bold]Path:[/bold] {escape(str(cx.path))}")
    agent_errs = collect_agent_errors(actual=cx.actual_min, events=cx.events)
    if agent_errs:
        lines.append("[bold]Agent errors:[/bold]")
        for err in agent_errs:
            lines.append(escape(err))
    lines.append(f"[bold]Expected:[/bold] {escape(str(cx.expected_summary))}")
    lines.append("[bold]Actual:[/bold]")
    body = format_actual_for_console(cx.actual_min)
    panel_inner = "\n".join(lines) + "\n\n" + escape(body)
    for n in cx.notes:
        panel_inner += "\n" + escape(n)
    if cx.events:
        trace_w = min(max(c.width - 6, 60), 120)
        trace_buf = io.StringIO()
        trace_console = Console(file=trace_buf, width=trace_w, highlight=False, force_terminal=False)
        panel_inner += "\n\n────────────────────────────────────────\n"
        print_rich_event_trace(trace_console, cx.events, title="Event trace")
        panel_inner += trace_buf.getvalue().rstrip("\n")
    c.print(
        Panel(
            Text.from_markup(panel_inner),
            title=f"[red]FAIL[/] {escape(_cli_job_label(r))} [{r.repeat_index}/{r.repeat_total}]",
            border_style="red",
            box=box.ROUNDED,
        )
    )


def _trial_counterexample(
    *,
    r: JobResult,
    trial: dict[str, Any],
) -> Counterexample:
    total_trials = len(r.fuzz_trials)
    trial_index = int(trial.get("trial_index", 0)) + 1
    turns = tuple(trial.get("turn_results") or ())
    raw_cx = trial.get("counterexample")
    if isinstance(raw_cx, dict):
        return Counterexample(
            headline=str(raw_cx.get("headline") or trial.get("failure_message") or "trial failed"),
            location=str(raw_cx.get("location") or f"trial {trial_index}"),
            path=(str(raw_cx["path"]) if raw_cx.get("path") is not None else None),
            expected_summary=str(raw_cx.get("expected_summary") or "expected trial to pass"),
            actual_min=raw_cx.get("actual_min"),
            notes=tuple(str(x) for x in (raw_cx.get("notes") or ())),
            check_kind=(str(raw_cx["check_kind"]) if raw_cx.get("check_kind") is not None else None),
            location_detail=(
                str(raw_cx["location_detail"])
                if raw_cx.get("location_detail") is not None
                else f"fuzz trial {trial_index}/{total_trials}"
            ),
            events=conversation_turns_to_event_trace(turns) if turns else None,
        )
    failure_kind = str(trial.get("failure_kind") or "trial_failure")
    failure_message = str(trial.get("failure_message") or "trial failed")
    actual: dict[str, Any] = {"trial_index": trial_index, "user_turns": list(trial.get("user_turns") or ())}
    if turns:
        actual["last_output"] = str(turns[-1].output) if turns[-1].output is not None else None
    notes: list[str] = []
    summary_label = trial.get("summary_label")
    if summary_label:
        notes.append(f"trial summary: {summary_label}")
    return Counterexample(
        headline=failure_message,
        location=f"trial {trial_index}",
        path=None,
        expected_summary=f"{failure_kind}: expected trial to pass",
        actual_min=actual,
        notes=tuple(notes),
        check_kind=failure_kind,
        location_detail=f"fuzz trial {trial_index}/{total_trials}",
        events=conversation_turns_to_event_trace(turns) if turns else None,
    )


def emit_trial_failure_detail(r: JobResult, *, file: TextIO | None = None) -> None:
    if not r.fuzz_trials:
        return
    for trial in r.fuzz_trials:
        if str(trial.get("status", "passed")) == "passed":
            continue
        trial_idx = int(trial.get("trial_index", 0)) + 1
        cx = _trial_counterexample(r=r, trial=trial)
        synthetic = JobResult(
            ok=False,
            scenario_name=r.scenario_name,
            case_id=r.case_id,
            repeat_index=r.repeat_index,
            repeat_total=r.repeat_total,
            detail=str(trial.get("failure_message") or r.detail),
            duration_s=float(trial.get("duration_s", 0.0) or 0.0),
            counterexample=Counterexample(
                headline=cx.headline,
                location=cx.location,
                path=cx.path,
                expected_summary=cx.expected_summary,
                actual_min=cx.actual_min,
                notes=cx.notes,
                check_kind=cx.check_kind,
                location_detail=f"{cx.location_detail} (repeat {r.repeat_index}/{r.repeat_total})",
                events=cx.events,
            ),
            param_cells=dict(r.param_cells),
        )
        emit_failure_detail(synthetic, file=file)


def emit_summary_table(results: Sequence[JobResult], *, file: TextIO | None = None) -> None:
    c = _console(file or sys.stdout)
    param_keys = _param_column_keys(results)
    tbl = Table(title="Results", box=box.SIMPLE_HEAD, show_lines=True)
    tbl.add_column("Test", style="bold", overflow="fold", max_width=56)
    for axis in param_keys:
        tbl.add_column(axis, overflow="fold", max_width=32)
    tbl.add_column("Repeat", justify="center")
    tbl.add_column("Trial", justify="center")
    tbl.add_column("Time (s)", justify="right")
    tbl.add_column("Result", justify="center")
    tbl.add_column("Failure (compact)", overflow="fold", max_width=56)
    for r in results:
        test_cell = r.scenario_name if param_keys else r.display_name
        rep = f"{r.repeat_index}/{r.repeat_total}"
        param_vals = [escape(_table_cell_compact(r.param_cells.get(p, "—"))) for p in param_keys]
        if r.fuzz_trials:
            total_trials = len(r.fuzz_trials)
            for trial in r.fuzz_trials:
                tix = int(trial.get("trial_index", 0)) + 1
                trial_status = str(trial.get("status", "passed"))
                trial_ok = trial_status == "passed"
                res_txt = "[green]pass[/]" if trial_ok else "[red]fail[/]"
                fail = "" if trial_ok else _failure_compact_for_trial(trial)
                td = float(trial.get("duration_s", 0.0) or 0.0)
                row = [
                    _table_cell_compact(test_cell),
                    *param_vals,
                    rep,
                    f"{tix}/{total_trials}",
                    f"{td:.2f}",
                    res_txt,
                    fail,
                ]
                tbl.add_row(*row)
        else:
            res_txt = "[green]pass[/]" if r.ok else "[red]fail[/]"
            fail = ""
            if not r.ok:
                fail = _failure_compact_for_table(r)
            row = [
                _table_cell_compact(test_cell),
                *param_vals,
                rep,
                "—",
                f"{r.duration_s:.2f}",
                res_txt,
                fail,
            ]
            tbl.add_row(*row)
    c.print(Rule(style="dim"))
    c.print(tbl)
    passed = sum(1 for x in results if x.ok)
    failed = sum(1 for x in results if not x.ok)
    c.print(
        Text.assemble(
            (f"{passed} passed", "green" if passed else "dim"),
            (", ", "dim"),
            (f"{failed} failed", "red" if failed else "dim"),
        )
    )


def emit_list_table(scenarios: Sequence["ScenarioDef"], *, file: TextIO | None = None) -> None:
    c = _console(file or sys.stdout)
    tbl = Table(title="Scenarios", box=box.SIMPLE_HEAD)
    tbl.add_column("Module", overflow="fold", max_width=40)
    tbl.add_column("Name", style="bold")
    tbl.add_column("Tags", overflow="fold", max_width=28)
    tbl.add_column("Repeats", justify="right")
    tbl.add_column("Timeout (s)", justify="right")
    for s in scenarios:
        tags = ",".join(s.tags) if s.tags else "—"
        to = "—" if s.timeout_s is None else str(s.timeout_s)
        tbl.add_row(s.module, s.name, tags, str(s.repeats), to)
    c.print(tbl)


__all__ = [
    "emit_error",
    "emit_failure_detail",
    "emit_job_compact",
    "emit_trial_failure_detail",
    "emit_list_table",
    "emit_note",
    "emit_summary_table",
]
