import { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ChevronLeft, ChevronRight } from "lucide-react";
import {
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
} from "@tanstack/react-table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { useExperiments, useRuns } from "@/api/queries";
import type { RunListItem } from "@/lib/types";
import { formatDateTime, formatDuration } from "@/lib/utils";
import { ColumnPicker } from "@/components/ColumnPicker";
import { useStoredColumnVisibility } from "@/lib/columnPrefs";
import { InlineError, InlineLoading, EmptyState } from "@/components/Inline";

const BASE_COLUMN_OPTIONS = [
  { id: "experiment_name", label: "Experiment", group: "Identity" },
  { id: "run_id", label: "Run ID", group: "Identity" },
  { id: "status", label: "Status", group: "Outcome" },
  { id: "scenarios", label: "Scenarios passed/total", group: "Outcome" },
  { id: "scenario_failed", label: "Scenarios failed", group: "Outcome" },
  { id: "repeat_pass_rate", label: "Repeat pass rate", group: "Outcome" },
  { id: "mean_duration_ms", label: "Mean repeat duration", group: "Timing" },
  { id: "started_at", label: "Started", group: "Timing" },
  { id: "finished_at", label: "Finished", group: "Timing" },
];

const PAGE_SIZE = 50;

function parseRunsListSearchParams(searchParams: URLSearchParams) {
  const experimentId = searchParams.get("experiment") ?? "";
  const status = searchParams.get("status") ?? "";
  const pageParam = searchParams.get("page");
  let page = 0;
  if (pageParam) {
    const n = Number.parseInt(pageParam, 10);
    if (Number.isFinite(n) && n > 1) page = n - 1;
  }
  return { experimentId, status, page };
}

function buildRunsListSearchParams(
  base: URLSearchParams,
  patch: { experiment?: string; status?: string; page?: number },
): URLSearchParams {
  const next = new URLSearchParams(base);
  if (patch.experiment !== undefined) {
    if (patch.experiment) next.set("experiment", patch.experiment);
    else next.delete("experiment");
  }
  if (patch.status !== undefined) {
    if (patch.status) next.set("status", patch.status);
    else next.delete("status");
  }
  if (patch.page !== undefined) {
    if (patch.page <= 0) next.delete("page");
    else next.set("page", String(patch.page + 1));
  }
  return next;
}

const DEFAULT_VISIBILITY: Record<string, boolean> = {
  experiment_name: true,
  run_id: true,
  status: true,
  scenarios: true,
  scenario_failed: false,
  repeat_pass_rate: true,
  mean_duration_ms: false,
  started_at: true,
  finished_at: false,
};

export function RunsListPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { experimentId, status, page } = parseRunsListSearchParams(searchParams);

  const updateParams = useCallback(
    (
      patch: { experiment?: string; status?: string; page?: number },
      opts?: { replace?: boolean },
    ) => {
      setSearchParams(buildRunsListSearchParams(searchParams, patch), {
        replace: opts?.replace ?? false,
      });
    },
    [searchParams, setSearchParams],
  );

  const [columnVisibility, setColumnVisibility] = useStoredColumnVisibility(
    "ask.runs.columnVisibility",
    DEFAULT_VISIBILITY,
  );
  const [sorting, setSorting] = useState<SortingState>([
    { id: "started_at", desc: true },
  ]);

  const experiments = useExperiments();
  const runs = useRuns({
    experiment_id: experimentId || undefined,
    status: status || undefined,
    limit: PAGE_SIZE,
    offset: page * PAGE_SIZE,
  });

  const runItems = runs.data?.items ?? [];
  const totalRuns = runs.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalRuns / PAGE_SIZE));
  const pageStart = totalRuns === 0 ? 0 : page * PAGE_SIZE + 1;
  const pageEnd = Math.min((page + 1) * PAGE_SIZE, totalRuns);

  useEffect(() => {
    if (!runs.data || totalRuns === 0 || page < totalPages) return;
    updateParams({ page: totalPages - 1 }, { replace: true });
  }, [page, runs.data, totalPages, totalRuns, updateParams]);

  const summaryKeys = useMemo(() => {
    const out = new Set<string>();
    for (const row of runItems) {
      for (const key of Object.keys(row.summary ?? {})) out.add(key);
    }
    return [...out].sort();
  }, [runItems]);

  const metadataKeys = useMemo(() => {
    const out = new Set<string>();
    for (const row of runItems) {
      for (const key of Object.keys(row.metadata ?? {})) out.add(key);
    }
    return [...out].sort();
  }, [runItems]);

  const columnOptions = useMemo(() => {
    const opts = [...BASE_COLUMN_OPTIONS];
    for (const key of summaryKeys) {
      opts.push({
        id: `summary:${key}`,
        label: `Summary: ${key}`,
        group: "Summary metrics",
      });
    }
    for (const key of metadataKeys) {
      opts.push({
        id: `metadata:${key}`,
        label: `Metadata: ${key}`,
        group: "Run metadata",
      });
    }
    return opts;
  }, [summaryKeys, metadataKeys]);

  useEffect(() => {
    const additions: Record<string, boolean> = {};
    for (const key of summaryKeys) {
      const colId = `summary:${key}`;
      if (!(colId in columnVisibility)) additions[colId] = false;
    }
    for (const key of metadataKeys) {
      const colId = `metadata:${key}`;
      if (!(colId in columnVisibility)) additions[colId] = false;
    }
    if (Object.keys(additions).length > 0) {
      setColumnVisibility({ ...columnVisibility, ...additions });
    }
  }, [columnVisibility, metadataKeys, setColumnVisibility, summaryKeys]);

  const columns = useMemo<ColumnDef<RunListItem>[]>(
    () => {
      const base: ColumnDef<RunListItem>[] = [
        {
        id: "experiment_name",
        header: "Experiment",
        accessorKey: "experiment_name",
        cell: ({ row }) => (
          <span className="font-medium">{row.original.experiment_name}</span>
        ),
      },
      {
        id: "run_id",
        header: "Run",
        accessorKey: "run_id",
        cell: ({ row }) => (
          <span className="text-slate-700 font-mono text-xs">
            {row.original.run_id}
          </span>
        ),
      },
      {
        id: "status",
        header: "Status",
        accessorKey: "status",
        cell: ({ row }) => <Badge status={row.original.status} />,
      },
      {
        id: "scenarios",
        header: "Scenarios",
        accessorFn: (r) => r.scenario_passed,
        cell: ({ row }) => (
          <span className="tabular-nums">
            {row.original.scenario_passed}
            <span className="text-slate-400"> / {row.original.scenario_count}</span>
          </span>
        ),
      },
      {
        id: "scenario_failed",
        header: "Failed",
        accessorKey: "scenario_failed",
        cell: ({ row }) => <span className="tabular-nums">{row.original.scenario_failed}</span>,
      },
      {
        id: "repeat_pass_rate",
        header: "Repeat pass",
        accessorKey: "repeat_pass_rate",
        cell: ({ row }) => (
          <span className="tabular-nums">
            {(row.original.repeat_pass_rate * 100).toFixed(1)}%
          </span>
        ),
      },
      {
        id: "mean_duration_ms",
        header: "Mean repeat",
        accessorKey: "mean_duration_ms",
        cell: ({ row }) => (
          <span className="tabular-nums text-slate-600">
            {formatDuration(row.original.mean_duration_ms)}
          </span>
        ),
      },
      {
        id: "started_at",
        header: "Started",
        accessorKey: "started_at",
        cell: ({ row }) => (
          <span className="text-slate-600">{formatDateTime(row.original.started_at)}</span>
        ),
      },
        {
        id: "finished_at",
        header: "Finished",
        accessorKey: "finished_at",
        cell: ({ row }) => (
          <span className="text-slate-600">{formatDateTime(row.original.finished_at)}</span>
        ),
        },
      ];

      for (const key of summaryKeys) {
        base.push({
          id: `summary:${key}`,
          header: key,
          accessorFn: (r) => r.summary?.[key] ?? null,
          cell: ({ row }) => {
            const value = row.original.summary?.[key];
            if (value == null) return <span className="text-slate-300">—</span>;
            if (typeof value === "number") {
              return <span className="tabular-nums text-slate-600">{value}</span>;
            }
            if (typeof value === "boolean") {
              return <span className="text-slate-600">{value ? "true" : "false"}</span>;
            }
            return (
              <span className="text-slate-600 max-w-[16rem] truncate inline-block align-bottom">
                {String(value)}
              </span>
            );
          },
        });
      }

      for (const key of metadataKeys) {
        base.push({
          id: `metadata:${key}`,
          header: key,
          accessorFn: (r) => r.metadata?.[key] ?? null,
          cell: ({ row }) => {
            const value = row.original.metadata?.[key];
            if (value == null) return <span className="text-slate-300">—</span>;
            if (typeof value === "number") {
              return <span className="tabular-nums text-slate-600">{value}</span>;
            }
            if (typeof value === "boolean") {
              return <span className="text-slate-600">{value ? "true" : "false"}</span>;
            }
            return (
              <span className="text-slate-600 max-w-[16rem] truncate inline-block align-bottom">
                {String(value)}
              </span>
            );
          },
        });
      }

      return base;
    },
    [metadataKeys, summaryKeys],
  );

  const table = useReactTable({
    data: runItems,
    columns,
    state: { columnVisibility, sorting },
    onColumnVisibilityChange: (updater) => {
      const next =
        typeof updater === "function" ? updater(columnVisibility) : updater;
      setColumnVisibility(next as Record<string, boolean>);
    },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <div className="mx-auto max-w-7xl flex flex-col gap-3">
      <div className="flex items-end justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Runs</h1>
          <p className="text-xs text-slate-500">
            Browse historical runs from the local result store.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select
            value={experimentId}
            onChange={(e) =>
              updateParams({ experiment: e.target.value, page: 0 })
            }
            disabled={experiments.isLoading || experiments.isError}
          >
            <option value="">All experiments</option>
            {(experiments.data ?? []).map((e) => (
              <option key={e.experiment_id} value={e.experiment_id}>
                {e.name}
              </option>
            ))}
          </Select>
          <Select
            value={status}
            onChange={(e) => updateParams({ status: e.target.value, page: 0 })}
          >
            <option value="">All statuses</option>
            <option value="passed">passed</option>
            <option value="failed">failed</option>
            <option value="error">error</option>
            <option value="timeout">timeout</option>
            <option value="skipped">skipped</option>
          </Select>
          <ColumnPicker
            options={columnOptions}
            visibility={columnVisibility}
            onToggle={(id, v) =>
              setColumnVisibility({ ...columnVisibility, [id]: v })
            }
          />
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
          <CardTitle className="text-sm font-medium">
            {runs.isLoading
              ? "Loading runs…"
              : totalRuns === 0
                ? "No runs"
                : totalRuns === 1
                  ? "1 run"
                  : `${totalRuns} runs`}
          </CardTitle>
          {totalRuns > PAGE_SIZE && (
            <div className="flex items-center gap-2 text-xs text-slate-600">
              <span className="tabular-nums">
                {pageStart}–{pageEnd} of {totalRuns}
              </span>
              <span className="text-slate-300">|</span>
              <span className="tabular-nums">
                Page {page + 1} of {totalPages}
              </span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                aria-label="Previous page"
                disabled={page === 0 || runs.isFetching}
                onClick={() => updateParams({ page: page - 1 })}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button
                type="button"
                variant="outline"
                size="sm"
                aria-label="Next page"
                disabled={page >= totalPages - 1 || runs.isFetching}
                onClick={() => updateParams({ page: page + 1 })}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          )}
        </CardHeader>
        <CardContent className="p-0">
          {runs.isLoading && <InlineLoading label="Fetching runs…" />}
          {runs.isError && (
            <InlineError error={runs.error} onRetry={() => runs.refetch()} />
          )}
          {!runs.isLoading && !runs.isError && totalRuns === 0 && (
            <EmptyState
              title="No runs yet"
              description="Run `agent-spec-kit run PATH` to record a run."
            />
          )}
          {!runs.isLoading && !runs.isError && runItems.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                  {table.getHeaderGroups().map((hg) => (
                    <tr key={hg.id}>
                      {hg.headers.map((h) => (
                        <th
                          key={h.id}
                          className="px-3 py-2 font-medium border-b border-slate-200 select-none cursor-pointer"
                          onClick={h.column.getToggleSortingHandler()}
                        >
                          <span className="inline-flex items-center gap-1">
                            {flexRender(h.column.columnDef.header, h.getContext())}
                            {h.column.getIsSorted() === "asc" && "↑"}
                            {h.column.getIsSorted() === "desc" && "↓"}
                          </span>
                        </th>
                      ))}
                    </tr>
                  ))}
                </thead>
                <tbody>
                  {table.getRowModel().rows.map((row) => (
                    <tr
                      key={row.id}
                      className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer"
                      onClick={() => navigate(`/runs/${row.original.run_id}`)}
                    >
                      {row.getVisibleCells().map((cell) => (
                        <td
                          key={cell.id}
                          className="px-3 py-2 align-middle"
                        >
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
