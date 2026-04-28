import { useMemo } from "react";
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
} from "@tanstack/react-table";
import type { ScenarioRow, RepeatSummary } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { formatDuration } from "@/lib/utils";

export interface ScenarioRepeatRow {
  scenario: ScenarioRow;
  repeat: RepeatSummary;
}

export function flattenScenarios(scenarios: ScenarioRow[]): ScenarioRepeatRow[] {
  const out: ScenarioRepeatRow[] = [];
  for (const s of scenarios) {
    if (!s.repeats || s.repeats.length === 0) {
      out.push({
        scenario: s,
        repeat: {
          repeat_result_id: "",
          repeat_index: 0,
          status: s.status,
          duration_ms: s.duration_ms ?? null,
          assertion_count: 0,
          assertion_passed: 0,
          failure_kind: null,
          failure_message: null,
        },
      });
      continue;
    }
    for (const r of s.repeats) out.push({ scenario: s, repeat: r });
  }
  return out;
}

export function collectParameterAxes(scenarios: ScenarioRow[]): string[] {
  const set = new Set<string>();
  for (const s of scenarios) {
    for (const k of Object.keys(s.parameters ?? {})) set.add(k);
  }
  return [...set].sort();
}

export interface ScenarioTableProps {
  scenarios: ScenarioRow[];
  visibility: Record<string, boolean>;
  onRowClick: (row: ScenarioRepeatRow) => void;
}

export function ScenarioTable({
  scenarios,
  visibility,
  onRowClick,
}: ScenarioTableProps) {
  const data = useMemo(() => flattenScenarios(scenarios), [scenarios]);
  const paramAxes = useMemo(() => collectParameterAxes(scenarios), [scenarios]);

  const columns = useMemo<ColumnDef<ScenarioRepeatRow>[]>(() => {
    const base: ColumnDef<ScenarioRepeatRow>[] = [
      {
        id: "scenario_name",
        header: "Scenario",
        accessorFn: (r) => r.scenario.scenario_name,
        cell: ({ row }) => (
          <div className="font-medium">{row.original.scenario.scenario_name}</div>
        ),
      },
      {
        id: "scenario_module",
        header: "Module",
        accessorFn: (r) => r.scenario.scenario_module ?? "—",
        cell: ({ row }) => (
          <span className="font-mono text-xs text-slate-500">
            {row.original.scenario.scenario_module ?? "—"}
          </span>
        ),
      },
      {
        id: "tags",
        header: "Tags",
        accessorFn: (r) => r.scenario.tags.join(","),
        cell: ({ row }) => (
          <div className="flex flex-wrap gap-1">
            {row.original.scenario.tags.map((t) => (
              <span
                key={t}
                className="text-[10px] uppercase tracking-wide text-slate-600 bg-slate-100 rounded px-1 py-0.5"
              >
                {t}
              </span>
            ))}
          </div>
        ),
      },
    ];
    for (const axis of paramAxes) {
      base.push({
        id: `param:${axis}`,
        header: axis,
        accessorFn: (r) => String(r.scenario.parameters[axis] ?? ""),
        cell: ({ row }) => (
          <span className="font-mono text-xs">
            {String(row.original.scenario.parameters[axis] ?? "—")}
          </span>
        ),
      });
    }
    base.push(
      {
        id: "repeat",
        header: "Repeat",
        accessorFn: (r) => r.repeat.repeat_index,
        cell: ({ row }) => (
          <span className="tabular-nums">
            {row.original.repeat.repeat_index}/{row.original.scenario.repeats_total}
          </span>
        ),
      },
      {
        id: "status",
        header: "Status",
        accessorFn: (r) => r.repeat.status,
        cell: ({ row }) => <Badge status={row.original.repeat.status} />,
      },
      {
        id: "duration",
        header: "Duration",
        accessorFn: (r) => r.repeat.duration_ms ?? 0,
        cell: ({ row }) => (
          <span className="text-slate-600 tabular-nums">
            {formatDuration(row.original.repeat.duration_ms)}
          </span>
        ),
      },
      {
        id: "failure_kind",
        header: "Failure kind",
        accessorFn: (r) => r.repeat.failure_kind ?? "",
        cell: ({ row }) =>
          row.original.repeat.failure_kind ? (
            <span className="text-rose-700 text-xs">
              {row.original.repeat.failure_kind}
            </span>
          ) : (
            <span className="text-slate-300">—</span>
          ),
      },
      {
        id: "failure_message",
        header: "Failure message",
        accessorFn: (r) => r.repeat.failure_message ?? "",
        cell: ({ row }) =>
          row.original.repeat.failure_message ? (
            <span className="text-xs text-rose-800/90 line-clamp-2">
              {row.original.repeat.failure_message}
            </span>
          ) : (
            <span className="text-slate-300">—</span>
          ),
      },
      {
        id: "assertions",
        header: "Assertions",
        accessorFn: (r) => `${r.repeat.assertion_passed}/${r.repeat.assertion_count}`,
        cell: ({ row }) => (
          <span className="tabular-nums text-slate-600">
            {row.original.repeat.assertion_passed}/{row.original.repeat.assertion_count}
          </span>
        ),
      },
      {
        id: "output_preview",
        header: "Output preview",
        accessorFn: (r) => r.repeat.output_preview ?? "",
        cell: ({ row }) => (
          <span className="text-xs text-slate-500 line-clamp-2">
            {row.original.repeat.output_preview ?? "—"}
          </span>
        ),
      },
    );
    return base;
  }, [paramAxes]);

  const table = useReactTable({
    data,
    columns,
    state: { columnVisibility: visibility },
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id}>
              {hg.headers.map((h) => (
                <th
                  key={h.id}
                  className="px-3 py-2 font-medium border-b border-slate-200"
                >
                  {flexRender(h.column.columnDef.header, h.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr
              key={row.id}
              onClick={() => onRowClick(row.original)}
              className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer"
            >
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-3 py-2 align-top max-w-[28rem]">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
