import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        side="right"
        className="flex flex-col p-0 max-w-[min(64rem,95vw)]"
      >
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
              {t.output_preview && (
                <div className="rounded-md border border-slate-200 bg-white p-3">
                  <div className="text-[11px] uppercase tracking-wide text-slate-500 mb-1">
                    Final output
                  </div>
                  <div className="text-sm whitespace-pre-wrap break-words">
                    {t.output_preview}
                  </div>
                </div>
              )}
              <section>
                <h3 className="text-sm font-semibold mb-2">Event trace</h3>
                <TraceTree roots={t.events as never} />
              </section>
              {t.assertions && t.assertions.length > 0 && (
                <section>
                  <h3 className="text-sm font-semibold mb-2">Assertions</h3>
                  <ul className="space-y-1.5">
                    {t.assertions.map((a) => (
                      <li
                        key={a.assertion_id}
                        className="rounded-md border border-slate-200 bg-white p-2 text-xs"
                      >
                        <div className="flex items-center gap-2">
                          <Badge status={a.status} />
                          <span className="font-mono text-slate-700">
                            {a.assertion_type}
                          </span>
                          {a.actor && (
                            <span className="text-slate-500">actor={a.actor}</span>
                          )}
                          {a.turn_index != null && (
                            <span className="text-slate-500">turn={a.turn_index}</span>
                          )}
                        </div>
                        {a.message && (
                          <div className="mt-1 text-slate-700 whitespace-pre-wrap">
                            {a.message}
                          </div>
                        )}
                      </li>
                    ))}
                  </ul>
                </section>
              )}
              {(t.status !== "passed" || t.counterexample || t.raw_error) && (
                <section>
                  <h3 className="text-sm font-semibold mb-2">Failure</h3>
                  <FailureCard
                    counterexample={t.counterexample}
                    rawError={t.raw_error}
                    blobErrors={t.blob_errors}
                    failureMessage={t.failure_message}
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
