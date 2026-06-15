import { useFuzzTrial } from "@/api/queries";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { InlineError, InlineLoading } from "@/components/Inline";
import { FuzzTrialTraceContent } from "@/components/FuzzTrialTraceContent";
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

      <Card>
        <CardContent className="pt-4 text-xs space-y-4">
          <FuzzTrialTraceContent trial={t} />
        </CardContent>
      </Card>
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
