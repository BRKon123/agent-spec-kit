import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useEffect, useRef, useState } from "react";
import type { MouseEvent as ReactMouseEvent } from "react";
import { Badge } from "@/components/ui/badge";
import { useFuzzTrial, useRepeatTrace } from "@/api/queries";
import { TraceTree } from "@/components/TraceTree";
import { FailureCard } from "@/components/FailureCard";
import { FuzzTrialTraceContent } from "@/components/FuzzTrialTraceContent";
import { InlineError, InlineLoading } from "@/components/Inline";
import { formatDuration } from "@/lib/utils";
import type { AgentEventNode } from "@/lib/types";

export function TraceDrawer({
  repeatId,
  fuzzTrialId,
  open,
  onOpenChange,
  onFuzzTrialSelect,
}: {
  repeatId: string | null;
  fuzzTrialId?: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onFuzzTrialSelect?: (trialId: string) => void;
}) {
  const trace = useRepeatTrace(fuzzTrialId ? undefined : (repeatId ?? undefined));
  const fuzzTrial = useFuzzTrial(fuzzTrialId ?? undefined);
  const t = trace.data;
  const ft = fuzzTrial.data;
  const hasFuzzTrials = Boolean(t?.fuzz_trials && t.fuzz_trials.length > 0);
  const [panelWidth, setPanelWidth] = useState<number>(760);
  const dragState = useRef<{ startX: number; startWidth: number } | null>(null);

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragState.current) return;
      const delta = dragState.current.startX - e.clientX;
      const next = dragState.current.startWidth + delta;
      setPanelWidth(Math.max(420, Math.min(window.innerWidth - 40, next)));
    };
    const onUp = () => {
      dragState.current = null;
      document.body.style.userSelect = "";
      document.body.style.cursor = "";
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, []);

  const onResizeStart = (e: ReactMouseEvent<HTMLDivElement>) => {
    dragState.current = { startX: e.clientX, startWidth: panelWidth };
    document.body.style.userSelect = "none";
    document.body.style.cursor = "col-resize";
  };

  const primaryAssertionType =
    t?.assertions?.find((a) => a.status !== "passed")?.assertion_type ??
    t?.assertions?.[0]?.assertion_type;

  const title = fuzzTrialId
    ? ft?.scenario_name ?? "Fuzz trial"
    : t?.scenario_key ?? "Trace";

  const description = fuzzTrialId && ft
    ? `Trial #${ft.trial_index}${ft.summary_label ? ` • ${ft.summary_label}` : ""} • ${formatDuration(ft.duration_ms)}${ft.failure_kind ? ` • ${ft.failure_kind}` : ""}`
    : t
      ? `Repeat ${t.repeat_index} • ${formatDuration(t.duration_ms)}${t.failure_kind ? ` • ${t.failure_kind}` : ""}`
      : "Loading trace details…";

  const status = fuzzTrialId && ft ? ft.status : t?.status;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        side="right"
        className="flex h-full max-h-screen flex-col p-0 max-w-none"
        style={{ width: `${panelWidth}px` }}
      >
        <div
          className="absolute left-0 top-0 h-full w-1.5 cursor-col-resize hover:bg-slate-200/80"
          onMouseDown={onResizeStart}
          title="Drag to resize panel"
        />
        <DialogHeader>
          <div className="flex items-center justify-between gap-3">
            <div className="min-w-0">
              <DialogTitle className="truncate">{title}</DialogTitle>
              <DialogDescription>{description}</DialogDescription>
            </div>
            {status && (
              <div className="flex items-center gap-2 pr-8">
                <Badge status={status} />
              </div>
            )}
          </div>
          {!fuzzTrialId && t && (t.tags.length > 0 || Object.keys(t.parameters).length > 0) && (
            <div className="flex flex-wrap items-center gap-1 mt-2">
              {Object.entries(t.parameters).map(([k, v]) => (
                <span
                  key={k}
                  className="text-[10px] font-mono text-slate-600 bg-slate-100 rounded px-1.5 py-0.5"
                >
                  {k}={String(v)}
                </span>
              ))}
              {t.tags.map((tag) => (
                <span
                  key={tag}
                  className="text-[10px] uppercase tracking-wide text-slate-600 bg-slate-100 rounded px-1.5 py-0.5"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
          {fuzzTrialId && ft && (
            <div className="flex flex-wrap items-center gap-1 mt-2">
              <span className="text-[10px] font-mono text-slate-600 bg-slate-100 rounded px-1.5 py-0.5">
                trial={ft.trial_index}
              </span>
              {ft.seed != null && (
                <span className="text-[10px] font-mono text-slate-600 bg-slate-100 rounded px-1.5 py-0.5">
                  seed={ft.seed}
                </span>
              )}
            </div>
          )}
        </DialogHeader>
        <div className="min-h-0 flex-1 overflow-y-auto p-4 space-y-4">
          {fuzzTrialId && fuzzTrial.isLoading && <InlineLoading label="Loading fuzz trial…" />}
          {fuzzTrialId && fuzzTrial.isError && (
            <InlineError error={fuzzTrial.error} onRetry={() => fuzzTrial.refetch()} />
          )}
          {fuzzTrialId && ft && <FuzzTrialTraceContent trial={ft} />}

          {!fuzzTrialId && trace.isLoading && <InlineLoading label="Loading trace…" />}
          {!fuzzTrialId && trace.isError && (
            <InlineError error={trace.error} onRetry={() => trace.refetch()} />
          )}
          {!fuzzTrialId && t && (
            <>
              {!hasFuzzTrials && t.output_preview && (
                <div className="rounded-md border border-slate-200 bg-white p-3">
                  <div className="text-[11px] uppercase tracking-wide text-slate-500 mb-1">
                    Final output
                  </div>
                  <div className="text-sm whitespace-pre-wrap break-words max-h-[min(40vh,24rem)] overflow-auto">
                    {t.output_preview}
                  </div>
                </div>
              )}
              {t.phase_errors && t.phase_errors.length > 0 && (
                <section>
                  <h3 className="text-sm font-semibold mb-2">Phase errors</h3>
                  <div className="space-y-2">
                    {t.phase_errors.map((pe) => (
                      <div
                        key={pe.phase_error_id}
                        className="rounded-md border border-rose-200 bg-rose-50/80 p-3 text-sm"
                      >
                        <div className="text-xs font-mono text-rose-700 mb-1">
                          {pe.phase}
                          {pe.sub_phase ? ` / ${pe.sub_phase}` : ""} · {pe.error_kind}
                        </div>
                        <div className="text-rose-900 whitespace-pre-wrap break-words">
                          {pe.message}
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              )}
              {t.fuzz_trials && t.fuzz_trials.length > 0 && (
                <section>
                  <h3 className="text-sm font-semibold mb-2">Fuzz trials</h3>
                  <p className="text-xs text-slate-500 mb-2">
                    Click a trial to view its event trace and failure details.
                  </p>
                  <div className="overflow-x-auto rounded-md border border-slate-200">
                    <table className="w-full text-xs">
                      <thead className="bg-slate-50 text-slate-500 text-left">
                        <tr>
                          <th className="px-2 py-1.5">#</th>
                          <th className="px-2 py-1.5">What</th>
                          <th className="px-2 py-1.5">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {t.fuzz_trials.map((trial) => (
                          <tr
                            key={trial.trial_id}
                            className="border-t border-slate-100 cursor-pointer hover:bg-slate-50"
                            onClick={() => onFuzzTrialSelect?.(trial.trial_id)}
                          >
                            <td className="px-2 py-1.5 tabular-nums">{trial.trial_index}</td>
                            <td className="px-2 py-1.5 text-slate-700">
                              {trial.summary_label || "—"}
                            </td>
                            <td className="px-2 py-1.5">
                              <Badge status={trial.status} />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              )}
              {!hasFuzzTrials && (
                <section>
                  <h3 className="text-sm font-semibold mb-2">Event trace</h3>
                  <TraceTree
                    transcript={t.transcript}
                    roots={
                      t.status !== "passed" &&
                      Array.isArray(t.counterexample?.events) &&
                      (t.counterexample?.events?.length ?? 0) > 0
                        ? (t.counterexample!.events as AgentEventNode[])
                        : null
                    }
                  />
                </section>
              )}
              {!hasFuzzTrials && (t.status !== "passed" || t.counterexample || t.raw_error) && (
                <section>
                  <h3 className="text-sm font-semibold mb-2">Failure</h3>
                  <FailureCard
                    counterexample={t.counterexample}
                    rawError={t.raw_error}
                    blobErrors={t.blob_errors}
                    failureMessage={t.failure_message}
                    assertionType={primaryAssertionType}
                  />
                </section>
              )}
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
