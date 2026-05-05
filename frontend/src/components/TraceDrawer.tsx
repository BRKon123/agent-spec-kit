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
import { useRepeatTrace } from "@/api/queries";
import { TraceTree } from "@/components/TraceTree";
import { FailureCard } from "@/components/FailureCard";
import { InlineError, InlineLoading } from "@/components/Inline";
import { formatDuration } from "@/lib/utils";

export function TraceDrawer({
  repeatId,
  open,
  onOpenChange,
}: {
  repeatId: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const trace = useRepeatTrace(repeatId ?? undefined);
  const t = trace.data;
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
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        side="right"
        className="flex flex-col p-0 max-w-none"
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
              <DialogTitle className="truncate">
                {t ? t.scenario_key : "Trace"}
              </DialogTitle>
              <DialogDescription>
                {t
                  ? `Repeat ${t.repeat_index} • ${formatDuration(t.duration_ms)}${t.failure_kind ? ` • ${t.failure_kind}` : ""}`
                  : "Loading trace details…"}
              </DialogDescription>
            </div>
            {t && (
              <div className="flex items-center gap-2 pr-8">
                <Badge status={t.status} />
              </div>
            )}
          </div>
          {t && (t.tags.length > 0 || Object.keys(t.parameters).length > 0) && (
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
        </DialogHeader>
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {trace.isLoading && <InlineLoading label="Loading trace…" />}
          {trace.isError && (
            <InlineError error={trace.error} onRetry={() => trace.refetch()} />
          )}
          {t && (
            <>
              {!hasFuzzTrials && t.output_preview && (
                <div className="rounded-md border border-slate-200 bg-white p-3">
                  <div className="text-[11px] uppercase tracking-wide text-slate-500 mb-1">
                    Final output
                  </div>
                  <div className="text-sm whitespace-pre-wrap break-words">
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
                        {t.fuzz_trials.map((ft) => (
                          <tr key={ft.trial_id} className="border-t border-slate-100">
                            <td className="px-2 py-1.5 tabular-nums">{ft.trial_index}</td>
                            <td className="px-2 py-1.5 text-slate-700">{ft.summary_label || "—"}</td>
                            <td className="px-2 py-1.5">
                              <Badge status={ft.status} />
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
                  <TraceTree transcript={t.transcript} />
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
