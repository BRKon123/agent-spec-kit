import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Plus, X } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useCompare, useExperiments } from "@/api/queries";
import type { CompareCell, CompareExperimentMeta } from "@/lib/types";
import { ColumnPicker, type ColumnPickerOption } from "@/components/ColumnPicker";
import { useStoredColumnVisibility } from "@/lib/columnPrefs";
import { TraceDrawer } from "@/components/TraceDrawer";
import { InlineError, InlineLoading, EmptyState } from "@/components/Inline";
import { cn, formatDuration } from "@/lib/utils";

const PER_EXP_FIELDS = [
  { id: "status", label: "Status" },
  { id: "repeats", label: "Repeats passed/total" },
  { id: "duration", label: "Latest duration" },
  { id: "failure_kind", label: "Failure kind" },
  { id: "failure_message", label: "Failure message" },
] as const;

const ROW_FIELDS = [
  { id: "scenario_name", label: "Scenario" },
  { id: "tags", label: "Tags" },
] as const;

export function ComparePage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const experiments = useExperiments();
  const [traceRepeatId, setTraceRepeatId] = useState<string | null>(null);
  const [traceOpen, setTraceOpen] = useState(false);

  const initialFromUrl = (searchParams.get("experiments") ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  const [selected, setSelected] = useState<string[]>(initialFromUrl);

  // Default to the two most-recent experiments once we have data.
  useEffect(() => {
    if (experiments.data && selected.length === 0 && experiments.data.length > 0) {
      const top = experiments.data.slice(0, Math.max(2, 2)).map((e) => e.experiment_id);
      while (top.length < 2 && top.length < experiments.data.length) {
        top.push(experiments.data[top.length].experiment_id);
      }
      setSelected(top.slice(0, Math.min(2, experiments.data.length)));
    }
  }, [experiments.data]); // eslint-disable-line react-hooks/exhaustive-deps

  // Keep URL in sync.
  useEffect(() => {
    const next = new URLSearchParams(searchParams);
    if (selected.length > 0) {
      next.set("experiments", selected.join(","));
    } else {
      next.delete("experiments");
    }
    setSearchParams(next, { replace: true });
  }, [selected]); // eslint-disable-line react-hooks/exhaustive-deps

  const compare = useCompare(selected);

  const columnOptions = useMemo<ColumnPickerOption[]>(() => {
    const opts: ColumnPickerOption[] = ROW_FIELDS.map((f) => ({
      id: f.id,
      label: f.label,
      group: "Row",
    }));
    for (const f of PER_EXP_FIELDS) {
      opts.push({ id: `cell:${f.id}`, label: `Per experiment: ${f.label}`, group: "Cells" });
    }
    return opts;
  }, []);

  const [columnVisibility, setColumnVisibility] = useStoredColumnVisibility(
    "ask.compare.columnVisibility",
    {
      scenario_name: true,
      tags: true,
      "cell:status": true,
      "cell:repeats": true,
      "cell:duration": false,
      "cell:failure_kind": true,
      "cell:failure_message": false,
    },
  );

  const setExperimentAt = (idx: number, value: string) => {
    if (selected.includes(value) && selected[idx] !== value) {
      toast.error("Experiment already selected", {
        description: "Each experiment can appear only once in the comparison.",
      });
      return;
    }
    setSelected((prev) => prev.map((x, i) => (i === idx ? value : x)));
  };
  const addExperimentSlot = () => {
    if (!experiments.data) return;
    const remaining = experiments.data.filter(
      (e) => !selected.includes(e.experiment_id),
    );
    if (remaining.length === 0) {
      toast("No more experiments to add");
      return;
    }
    setSelected((prev) => [...prev, remaining[0].experiment_id]);
  };
  const removeExperimentAt = (idx: number) => {
    setSelected((prev) => prev.filter((_, i) => i !== idx));
  };

  const onCellClick = (cell: CompareCell | null) => {
    if (!cell || !cell.latest_repeat) return;
    setTraceRepeatId(cell.latest_repeat.repeat_result_id);
    setTraceOpen(true);
  };

  return (
    <div className="mx-auto max-w-[110rem] flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Compare experiments</h1>
          <p className="text-xs text-slate-500">
            Pick two or more experiments. Cells show the most recent repeat for
            each scenario in each experiment.
          </p>
        </div>
        <ColumnPicker
          options={columnOptions}
          visibility={columnVisibility}
          onToggle={(id, v) =>
            setColumnVisibility({ ...columnVisibility, [id]: v })
          }
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Experiments</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-2 items-center">
          {experiments.isLoading && <InlineLoading label="Loading experiments…" />}
          {experiments.isError && (
            <InlineError
              error={experiments.error}
              onRetry={() => experiments.refetch()}
            />
          )}
          {experiments.data &&
            selected.map((id, idx) => (
              <div key={idx} className="flex items-center gap-1.5">
                <Select
                  value={id}
                  onChange={(e) => setExperimentAt(idx, e.target.value)}
                >
                  {experiments.data!.map((e) => (
                    <option key={e.experiment_id} value={e.experiment_id}>
                      {e.name}
                    </option>
                  ))}
                </Select>
                <Button
                  size="icon"
                  variant="ghost"
                  onClick={() => removeExperimentAt(idx)}
                  disabled={selected.length <= 2}
                  title={
                    selected.length <= 2
                      ? "Need at least two experiments"
                      : "Remove"
                  }
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
          {experiments.data && (
            <Button
              variant="outline"
              size="sm"
              onClick={addExperimentSlot}
              disabled={
                selected.length >= (experiments.data?.length ?? 0)
              }
            >
              <Plus className="h-4 w-4" /> Add experiment
            </Button>
          )}
        </CardContent>
      </Card>

      {selected.length < 2 ? (
        <EmptyState
          title="Pick at least two experiments"
          description="Use the dropdowns above to compare two or more experiments side by side."
        />
      ) : compare.isLoading ? (
        <InlineLoading label="Loading comparison…" />
      ) : compare.isError ? (
        <InlineError error={compare.error} onRetry={() => compare.refetch()} />
      ) : compare.data ? (
        <CompareTableView
          experiments={compare.data.experiments}
          rows={compare.data.rows}
          columnVisibility={columnVisibility}
          onCellClick={onCellClick}
        />
      ) : null}

      <TraceDrawer
        repeatId={traceRepeatId}
        open={traceOpen}
        onOpenChange={setTraceOpen}
      />
    </div>
  );
}

function CompareTableView({
  experiments,
  rows,
  columnVisibility,
  onCellClick,
}: {
  experiments: CompareExperimentMeta[];
  rows: import("@/lib/types").CompareRow[];
  columnVisibility: Record<string, boolean>;
  onCellClick: (cell: CompareCell | null) => void;
}) {
  if (rows.length === 0) {
    return (
      <EmptyState
        title="No scenarios to compare"
        description="No scenarios were found across the selected experiments."
      />
    );
  }
  const showField = (id: string) => columnVisibility[id] ?? true;
  const cellFieldVisible = (id: string) => columnVisibility[`cell:${id}`] ?? true;
  const [hoveredExperimentGroup, setHoveredExperimentGroup] = useState<string | null>(null);

  return (
    <Card>
      <CardContent className="p-0 overflow-x-auto">
        <table className="min-w-max text-sm border-separate border-spacing-0">
          <thead>
            <tr className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              {showField("scenario_name") && (
                <th className="sticky left-0 z-10 bg-slate-50 text-left px-3 py-2 border-b border-slate-200 min-w-[16rem] whitespace-nowrap">
                  Scenario
                </th>
              )}
              {showField("tags") && (
                <th className="text-left px-3 py-2 border-b border-slate-200 min-w-[10rem] whitespace-nowrap">
                  Tags
                </th>
              )}
              {experiments.map((e) => (
                <th
                  key={e.experiment_id}
                  colSpan={PER_EXP_FIELDS.filter((f) => cellFieldVisible(f.id)).length}
                  className="text-left px-3 py-2 border-b border-slate-200 border-l border-slate-200 whitespace-nowrap"
                >
                  {e.name}
                  <div className="text-[10px] normal-case text-slate-400 font-normal">
                    {e.latest_run_id ?? "no runs"}
                  </div>
                </th>
              ))}
            </tr>
            <tr className="bg-slate-50 text-[10px] uppercase tracking-wide text-slate-500">
              {showField("scenario_name") && <th className="sticky left-0 bg-slate-50" />}
              {showField("tags") && <th />}
              {experiments.map((e) =>
                PER_EXP_FIELDS.filter((f) => cellFieldVisible(f.id)).map((f, i) => (
                  <th
                    key={`${e.experiment_id}:${f.id}`}
                    className={cn(
                      "text-left px-3 py-1 border-b border-slate-200",
                      i === 0 && "border-l border-slate-200",
                    )}
                  >
                    {f.label}
                  </th>
                )),
              )}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const statuses = experiments
                .map((e) => row.cells[e.experiment_id]?.scenario_status)
                .filter((s): s is NonNullable<typeof s> => Boolean(s));
              const distinct = new Set(statuses);
              const mismatch = distinct.size > 1;
              return (
                <tr
                  key={`${row.scenario_key}|${row.parameter_key}`}
                  className={cn(
                    "border-b border-slate-100",
                    mismatch && "bg-amber-50/60",
                  )}
                >
                  {showField("scenario_name") && (
                    <td
                      className={cn(
                        "sticky left-0 bg-white px-3 py-2 align-top border-b border-slate-100 min-w-[16rem] overflow-hidden",
                        mismatch && "bg-amber-50/60 border-l-2 border-l-amber-400",
                      )}
                    >
                      <div className="font-medium whitespace-nowrap">
                        {row.scenario_name}
                      </div>
                      {row.parameter_key && row.parameter_key !== "default" && (
                        <div className="text-[11px] font-mono text-slate-500 whitespace-nowrap">
                          {row.parameter_key}
                        </div>
                      )}
                      {mismatch && (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span className="text-[10px] text-amber-700 font-medium uppercase tracking-wide">
                              statuses differ
                            </span>
                          </TooltipTrigger>
                          <TooltipContent>
                            {[...distinct].join(", ")}
                          </TooltipContent>
                        </Tooltip>
                      )}
                    </td>
                  )}
                  {showField("tags") && (
                    <td
                      className={cn(
                        "px-3 py-2 align-top border-b border-slate-100 overflow-hidden",
                      )}
                    >
                      <div className="flex flex-wrap gap-1 min-w-[10rem]">
                        {row.tags.map((t) => (
                          <span
                            key={t}
                            className="text-[10px] uppercase tracking-wide text-slate-600 bg-slate-100 rounded px-1 py-0.5"
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    </td>
                  )}
                  {experiments.map((e) => {
                    const cell = row.cells[e.experiment_id];
                    const experimentGroupKey = `${row.scenario_key}|${row.parameter_key}|${e.experiment_id}`;
                    const isExperimentHovered = hoveredExperimentGroup === experimentGroupKey;
                    return PER_EXP_FIELDS.filter((f) => cellFieldVisible(f.id)).map(
                      (f, i) => (
                        <td
                          key={`${row.scenario_key}|${e.experiment_id}|${f.id}`}
                          className={cn(
                            "px-3 py-2 align-top border-b border-slate-100 max-w-[18rem] overflow-hidden",
                            i === 0 && "border-l border-slate-200",
                            isExperimentHovered && "bg-slate-100/60",
                            cell?.latest_repeat && "cursor-pointer",
                          )}
                          onMouseEnter={() => setHoveredExperimentGroup(experimentGroupKey)}
                          onMouseLeave={() => setHoveredExperimentGroup((prev) =>
                            prev === experimentGroupKey ? null : prev,
                          )}
                          onClick={() => onCellClick(cell ?? null)}
                        >
                          {cell ? (
                            <CompareCellView field={f.id} cell={cell} />
                          ) : (
                            <span className="text-slate-300">—</span>
                          )}
                        </td>
                      ),
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}

function CompareCellView({ field, cell }: { field: string; cell: CompareCell }) {
  switch (field) {
    case "status":
      return <Badge status={cell.scenario_status} />;
    case "repeats":
      return (
        <span className="tabular-nums text-xs">
          {cell.repeats_passed}
          <span className="text-slate-400"> / {cell.repeats_total}</span>
        </span>
      );
    case "duration":
      return (
        <span className="tabular-nums text-xs text-slate-600">
          {formatDuration(cell.latest_repeat?.duration_ms ?? cell.scenario_duration_ms ?? null)}
        </span>
      );
    case "failure_kind":
      return cell.latest_repeat?.failure_kind ? (
        <span className="text-xs text-rose-700">{cell.latest_repeat.failure_kind}</span>
      ) : (
        <span className="text-slate-300">—</span>
      );
    case "failure_message":
      return cell.latest_repeat?.failure_message ? (
        <span className="text-xs text-rose-800/80 line-clamp-2">
          {cell.latest_repeat.failure_message}
        </span>
      ) : (
        <span className="text-slate-300">—</span>
      );
    default:
      return null;
  }
}
