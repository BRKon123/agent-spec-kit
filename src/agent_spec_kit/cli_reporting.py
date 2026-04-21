"""Rich-based console output for ``agent-spec-kit run``."""

from __future__ import annotations

import io
import json
import sys
from collections.abc import Sequence
from typing import TYPE_CHECKING, TextIO

from rich import box
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from agent_spec_kit.events import print_rich_event_trace

if TYPE_CHECKING:
    from agent_spec_kit.registries import ScenarioDef
    from agent_spec_kit.runner import JobResult


def _console(file: TextIO | None = None) -> Console:
    return Console(file=file, highlight=False)


def emit_error(msg: str, *, file: TextIO | None = None) -> None:
    c = _console(file or sys.stderr)
    c.print(f"[red]{msg}[/]")


def emit_note(msg: str, *, file: TextIO | None = None) -> None:
    c = _console(file or sys.stderr)
    c.print(f"[dim]{msg}[/]")


def emit_job_compact(r: "JobResult", *, file: TextIO | None = None) -> None:
    c = _console(file or sys.stdout)
    bracket = f"[{r.repeat_index}/{r.repeat_total}]"
    t = f" {r.duration_s:.2f}s"
    if r.ok:
        c.print(Text.assemble(("PASS ", "bold green"), (r.scenario_name, "bold"), (" ", "dim"), (bracket, "dim"), (t, "dim")))
    else:
        tail = r.detail or ""
        if len(tail) > 120:
            tail = tail[:117] + "..."
        c.print(
            Text.assemble(
                ("FAIL ", "bold red"),
                (r.scenario_name, "bold"),
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
        return kind
    return _table_cell_compact(r.detail or "")


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
        lines.append(f"[bold]Path:[/bold] {escape(cx.path)}")
    lines.append(f"[bold]Expected:[/bold] {escape(str(cx.expected_summary))}")
    lines.append("[bold]Actual:[/bold]")
    body = str(cx.actual_min)
    try:
        parsed = json.loads(body)
        body = json.dumps(parsed, indent=2, default=str)
    except (json.JSONDecodeError, TypeError):
        pass
    panel_inner = "\n".join(lines) + "\n\n" + escape(body)
    for n in cx.notes:
        panel_inner += "\n" + escape(n)
    if cx.events:
        trace_w = min(max(c.width - 6, 60), 120)
        trace_buf = io.StringIO()
        trace_console = Console(file=trace_buf, width=trace_w, highlight=False, force_terminal=False)
        panel_inner += "\n\n────────────────────────────────────────\n"
        panel_inner += "[bold]Event trace[/bold]\n"
        print_rich_event_trace(trace_console, cx.events, title="")
        panel_inner += trace_buf.getvalue().rstrip("\n")
    c.print(
        Panel(
            Text.from_markup(panel_inner),
            title=f"[red]FAIL[/] {escape(r.scenario_name)} [{r.repeat_index}/{r.repeat_total}]",
            border_style="red",
            box=box.ROUNDED,
        )
    )


def emit_summary_table(results: Sequence["JobResult"], *, file: TextIO | None = None) -> None:
    c = _console(file or sys.stdout)
    tbl = Table(title="Results", box=box.SIMPLE_HEAD, show_lines=True)
    tbl.add_column("Test", style="bold", overflow="fold", max_width=56)
    tbl.add_column("Repeat", justify="center")
    tbl.add_column("Time (s)", justify="right")
    tbl.add_column("Result", justify="center")
    tbl.add_column("Failure (compact)", overflow="fold", max_width=56)
    for r in results:
        rep = f"{r.repeat_index}/{r.repeat_total}"
        res_txt = "[green]pass[/]" if r.ok else "[red]fail[/]"
        fail = ""
        if not r.ok:
            fail = _failure_compact_for_table(r)
        tbl.add_row(_table_cell_compact(r.scenario_name), rep, f"{r.duration_s:.2f}", res_txt, fail)
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
    "emit_list_table",
    "emit_note",
    "emit_summary_table",
]
