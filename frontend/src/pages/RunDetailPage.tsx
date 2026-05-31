import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ChevronLeft, PanelRightClose, PanelRightOpen } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useFuzzTrialsForRun, useRun, useScenariosForRun } from "@/api/queries";
import { ApiError } from "@/api/http";
import {
  ScenarioTable,
  collectParameterAxes,
} from "@/components/ScenarioTable";
import { ColumnPicker, type ColumnPickerOption } from "@/components/ColumnPicker";
import { useStoredColumnVisibility } from "@/lib/columnPrefs";
import { InlineError, InlineLoading, EmptyState } from "@/components/Inline";
import { FuzzTrialSidePanel } from "@/components/FuzzTrialSidePanel";
import { RunSidePanel } from "@/components/RunSidePanel";
import { TraceDrawer } from "@/components/TraceDrawer";
import { NotFoundPage } from "@/pages/NotFoundPage";
import type { ScenarioRow } from "@/lib/types";
import { formatDateTime, formatDuration } from "@/lib/utils";

const BASE_OPTIONS: ColumnPickerOption[] = [
  { id: "scenario_name", label: "Scenario", group: "Identity" },
  { id: "scenario_module", label: "Module", group: "Identity" },
  { id: "tags", label: "Tags", group: "Identity" },
  { id: "repeat", label: "Repeat #", group: "Outcome" },
  { id: "status", label: "Status", group: "Outcome" },
  { id: "duration", label: "Duration", group: "Outcome" },
  { id: "failure_kind", label: "Failure kind", group: "Outcome" },
  { id: "failure_message", label: "Failure message", group: "Outcome" },
  { id: "assertions", label: "Assertions", group: "Outcome" },
  { id: "output_preview", label: "Output preview", group: "Outcome" },
];

const DEFAULT_VISIBILITY: Record<string, boolean> = {
  scenario_name: true,
  scenario_module: false,
  tags: true,
  repeat: true,
  status: true,
  duration: true,
  failure_kind: true,
  failure_message: false,
  assertions: false,
  output_preview: false,
};

export function RunDetailPage() {
  const { runId = "" } = useParams<{ runId: string }>();
  const run = useRun(runId);
  const scenarios = useScenariosForRun(runId);
  const fuzzTrials = useFuzzTrialsForRun(runId);
  const [sideOpen, setSideOpen] = useState(true);
  const [traceRepeatId, setTraceRepeatId] = useState<string | null>(null);
  const [traceFuzzTrialId, setTraceFuzzTrialId] = useState<string | null>(null);
  const [traceOpen, setTraceOpen] = useState(false);
  const [selectedTrialId, setSelectedTrialId] = useState<string | null>(null);

  const paramAxes = useMemo(
    () => collectParameterAxes(scenarios.data ?? []),
    [scenarios.data],
  );

  const columnOptions = useMemo<ColumnPickerOption[]>(() => {
    const opts = [...BASE_OPTIONS];
    for (const axis of paramAxes) {
      opts.push({ id: `param:${axis}`, label: `Param: ${axis}`, group: "Parameters" });
    }
    return opts;
  }, [paramAxes]);

  const initialVisibility = useMemo<Record<string, boolean>>(() => {
    const v = { ...DEFAULT_VISIBILITY };
    for (const axis of paramAxes) v[`param:${axis}`] = true;
    return v;
  }, [paramAxes]);

  const [columnVisibility, setColumnVisibility] = useStoredColumnVisibility(
    "ask.scenarios.columnVisibility",
    initialVisibility,
  );

  if (run.isError && run.error instanceof ApiError && run.error.status === 404) {
    return (
      <NotFoundPage
        title="Run not found"
        detail={`No run with id "${runId}" in the local store.`}
      />
    );
  }

  const onScenarioRowClick = (scenario: ScenarioRow) => {
    const preferred =
      scenario.repeats.find((r) => r.status !== "passed") ?? scenario.repeats[0];
    if (!preferred?.repeat_result_id) return;
    setSelectedTrialId(null);
    setTraceFuzzTrialId(null);
    setTraceRepeatId(preferred.repeat_result_id);
    setTraceOpen(true);
  };

  const onTrialRowClick = (trialId: string) => {
    setSelectedTrialId(trialId);
    setTraceRepeatId(null);
    setTraceFuzzTrialId(trialId);
    setTraceOpen(true);
  };

  return (
    <div className="mx-auto max-w-[110rem] flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <Button asChild variant="ghost" size="sm">
            <Link to="/">
              <ChevronLeft className="h-4 w-4" /> Runs
            </Link>
          </Button>
          <div>
            <h1 className="text-xl font-semibold tracking-tight font-mono">
              {runId}
            </h1>
            {run.data && (
              <p className="text-xs text-slate-500">
                {run.data.experiment_name} • {formatDateTime(run.data.started_at)}{" "}
                {run.data.finished_at &&
                  ` → ${formatDateTime(run.data.finished_at)}`}
                {run.data.summary &&
                  ` • mean repeat ${formatDuration(Number(run.data.summary.mean_duration_ms ?? 0))}`}
              </p>
            )}
          </div>
          {run.data && <Badge status={run.data.status} />}
        </div>
        <div className="flex items-center gap-2">
          <ColumnPicker
            options={columnOptions}
            visibility={columnVisibility}
            onToggle={(id, v) =>
              setColumnVisibility({ ...columnVisibility, [id]: v })
            }
          />
          <Button
            variant="outline"
            size="sm"
            onClick={() => setSideOpen((v) => !v)}
            title={sideOpen ? "Hide details" : "Show details"}
          >
            {sideOpen ? (
              <PanelRightClose className="h-4 w-4" />
            ) : (
              <PanelRightOpen className="h-4 w-4" />
            )}
            Details
          </Button>
        </div>
      </div>

      <div
        className="grid gap-3"
        style={{
          gridTemplateColumns: sideOpen ? "minmax(0,1fr) 22rem" : "minmax(0,1fr)",
        }}
      >
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">
              {scenarios.data
                ? `${scenarios.data.length} scenarios`
                : "Loading scenarios…"}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {scenarios.isLoading && <InlineLoading label="Fetching scenarios…" />}
            {scenarios.isError && (
              <InlineError
                error={scenarios.error}
                onRetry={() => scenarios.refetch()}
              />
            )}
            {scenarios.data && scenarios.data.length === 0 && (
              <EmptyState
                title="No scenarios in this run"
                description="The run completed without recording any scenarios."
              />
            )}
            {scenarios.data && scenarios.data.length > 0 && (
              <ScenarioTable
                scenarios={scenarios.data}
                fuzzTrials={fuzzTrials.data ?? []}
                visibility={columnVisibility}
                onScenarioRowClick={onScenarioRowClick}
                onTrialRowClick={onTrialRowClick}
              />
            )}
          </CardContent>
        </Card>

        {sideOpen && (
          <aside>
            {run.isLoading && <InlineLoading label="Loading run details…" />}
            {run.isError && !(run.error instanceof ApiError && run.error.status === 404) && (
              <InlineError error={run.error} onRetry={() => run.refetch()} />
            )}
            {selectedTrialId ? (
              <FuzzTrialSidePanel trialId={selectedTrialId} />
            ) : (
              run.data && <RunSidePanel run={run.data} />
            )}
          </aside>
        )}
      </div>

      <TraceDrawer
        repeatId={traceRepeatId}
        fuzzTrialId={traceFuzzTrialId}
        open={traceOpen}
        onOpenChange={(open) => {
          setTraceOpen(open);
          if (!open) {
            setTraceFuzzTrialId(null);
            setTraceRepeatId(null);
          }
        }}
        onFuzzTrialSelect={onTrialRowClick}
      />
    </div>
  );
}
