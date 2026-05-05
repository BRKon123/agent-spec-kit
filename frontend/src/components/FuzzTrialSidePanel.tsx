import { useFuzzTrial } from "@/api/queries";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { InlineError, InlineLoading } from "@/components/Inline";
import { TraceTree } from "@/components/TraceTree";
import { FailureCard } from "@/components/FailureCard";
import { JsonView } from "@/components/JsonView";
import { formatDuration } from "@/lib/utils";

export function FuzzTrialSidePanel({
  trialId,
}: {
  trialId: string;
}) {
  const q = useFuzzTrial(trialId);

  if (q.isLoading) return <InlineLoading label="Loading trial details…" />;
  if (q.isError) return <InlineError error={q.error} onRetry={() => q.refetch()} />;
  const t = q.data;
  if (!t) return null;

  return (
    <div className="flex flex-col gap-3">
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle className="text-sm">Fuzz trial #{t.trial_index}</CardTitle>
          <Badge status={t.status} />
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-2 text-xs">
          <KV k="Scenario" v={t.scenario_name ?? "—"} />
          <KV k="Repeat" v={<span className="font-mono">{t.repeat_result_id}</span>} />
          <KV k="Trial ID" v={<span className="font-mono">{t.trial_id}</span>} />
          <KV k="Seed" v={String(t.seed ?? "—")} />
          <KV k="Duration" v={formatDuration(t.duration_ms)} />
          <KV k="Summary" v={t.summary_label || "—"} />
          {t.failure_kind && <KV k="Failure kind" v={t.failure_kind} />}
          {t.failure_message && <KV k="Failure message" v={t.failure_message} />}
        </CardContent>
      </Card>

      {t.user_turns?.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">User turns</CardTitle>
          </CardHeader>
          <CardContent className="text-xs">
            <ol className="list-decimal list-inside space-y-1">
              {t.user_turns.map((u, i) => (
                <li key={i} className="whitespace-pre-wrap break-words">
                  {u}
                </li>
              ))}
            </ol>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Event trace</CardTitle>
        </CardHeader>
        <CardContent className="text-xs space-y-2">
          <TraceTree transcript={t.transcript} />
          {Object.keys(t.blob_errors ?? {}).length > 0 && (
            <div>
              <div className="text-[11px] uppercase tracking-wide text-slate-500 mb-1">
                Blob errors
              </div>
              <JsonView value={t.blob_errors} />
            </div>
          )}
        </CardContent>
      </Card>

      {(t.status !== "passed" || t.failure_message || t.failure_kind) && (
        <section>
          <h3 className="text-sm font-semibold mb-2">Failure</h3>
          <FailureCard
            counterexample={null}
            rawError={null}
            blobErrors={t.blob_errors ?? {}}
            failureMessage={t.failure_message ?? null}
            assertionType={t.failure_kind ?? null}
          />
        </section>
      )}
    </div>
  );
}

function KV({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex gap-2">
      <div className="w-24 shrink-0 text-slate-500">{k}</div>
      <div className="flex-1 break-words">{v}</div>
    </div>
  );
}
