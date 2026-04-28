import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { RunDetail } from "@/lib/types";
import { formatDateTime, formatDuration } from "@/lib/utils";
import { JsonView } from "@/components/JsonView";

export function RunSidePanel({ run }: { run: RunDetail }) {
  const summary = run.summary as Record<string, unknown>;
  const num = (k: string) => Number(summary[k] ?? 0);
  const failureKinds = (summary.failure_kinds ?? {}) as Record<string, number>;
  const tagBreakdown = (summary.tag_breakdown ?? {}) as Record<string, number>;
  const paramBreakdown = (summary.parameter_breakdown ?? {}) as Record<
    string,
    Record<string, { repeat_count: number; repeat_passed: number; repeat_pass_rate: number }>
  >;
  return (
    <div className="flex flex-col gap-3">
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle className="text-sm">Run summary</CardTitle>
          <Badge status={run.status} />
        </CardHeader>
        <CardContent className="grid grid-cols-2 gap-3 text-xs">
          <Stat label="Scenarios">
            <span className="tabular-nums">
              {num("scenario_passed")} / {num("scenario_count")} passed
            </span>
          </Stat>
          <Stat label="Repeats">
            <span className="tabular-nums">
              {num("repeat_passed")} / {num("repeat_count")} passed
            </span>
          </Stat>
          <Stat label="Repeat pass rate">
            <span className="tabular-nums">
              {(num("repeat_pass_rate") * 100).toFixed(1)}%
            </span>
          </Stat>
          <Stat label="Flaky scenarios">
            <span className="tabular-nums">{num("flaky_scenarios")}</span>
          </Stat>
          <Stat label="Mean repeat">
            <span className="tabular-nums">
              {formatDuration(num("mean_duration_ms"))}
            </span>
          </Stat>
          <Stat label="p50 / p95">
            <span className="tabular-nums">
              {formatDuration(num("p50_duration_ms"))} /{" "}
              {formatDuration(num("p95_duration_ms"))}
            </span>
          </Stat>
          <Stat label="Started">{formatDateTime(run.started_at)}</Stat>
          <Stat label="Finished">{formatDateTime(run.finished_at)}</Stat>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Run metadata</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-2 text-xs">
          <KV k="Run ID" v={<span className="font-mono">{run.run_id}</span>} />
          <KV k="Experiment" v={run.experiment_name} />
          <KV k="Python" v={run.python_version ?? "—"} />
          <KV k="Package" v={run.package_version ?? "—"} />
          <KV
            k="Git"
            v={
              run.git_branch
                ? `${run.git_branch}${run.git_commit ? ` @ ${run.git_commit.slice(0, 7)}` : ""}${run.git_dirty ? " (dirty)" : ""}`
                : "—"
            }
          />
          {run.command && (
            <KV
              k="Command"
              v={<span className="font-mono break-all">{run.command}</span>}
            />
          )}
          {run.notes && <KV k="Notes" v={run.notes} />}
          {Object.keys(run.metadata ?? {}).length > 0 && (
            <div className="mt-1">
              <div className="text-[11px] uppercase tracking-wide text-slate-500 mb-1">
                User metadata
              </div>
              <JsonView value={run.metadata} />
            </div>
          )}
        </CardContent>
      </Card>

      {Object.keys(failureKinds).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Failure kinds</CardTitle>
          </CardHeader>
          <CardContent className="text-xs flex flex-wrap gap-1.5">
            {Object.entries(failureKinds).map(([k, n]) => (
              <span
                key={k}
                className="inline-flex items-center gap-1 rounded-full border border-rose-200 bg-rose-50 px-2 py-0.5 text-rose-700"
              >
                {k}
                <span className="tabular-nums opacity-70">×{n}</span>
              </span>
            ))}
          </CardContent>
        </Card>
      )}

      {Object.keys(tagBreakdown).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Tag breakdown</CardTitle>
          </CardHeader>
          <CardContent className="text-xs flex flex-wrap gap-1.5">
            {Object.entries(tagBreakdown).map(([k, n]) => (
              <span
                key={k}
                className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-slate-700"
              >
                {k}
                <span className="tabular-nums opacity-70">×{n}</span>
              </span>
            ))}
          </CardContent>
        </Card>
      )}

      {Object.keys(paramBreakdown).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Parameter breakdown</CardTitle>
          </CardHeader>
          <CardContent className="text-xs flex flex-col gap-2">
            {Object.entries(paramBreakdown).map(([axis, entries]) => (
              <div key={axis}>
                <div className="text-[11px] uppercase tracking-wide text-slate-500">
                  {axis}
                </div>
                <ul className="mt-1 space-y-0.5">
                  {Object.entries(entries).map(([val, info]) => (
                    <li key={val} className="flex justify-between">
                      <span className="font-mono">{val}</span>
                      <span className="tabular-nums text-slate-600">
                        {info.repeat_passed}/{info.repeat_count}{" "}
                        ({(info.repeat_pass_rate * 100).toFixed(0)}%)
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function Stat({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="text-sm mt-0.5">{children}</div>
    </div>
  );
}

function KV({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex gap-2">
      <div className="w-20 shrink-0 text-slate-500">{k}</div>
      <div className="flex-1 break-words">{v}</div>
    </div>
  );
}
