import { useFuzzTrialsForRun } from "@/api/queries";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { InlineError, InlineLoading } from "@/components/Inline";

export function FuzzTrialsPanel({ runId }: { runId: string }) {
  const q = useFuzzTrialsForRun(runId);
  if (q.isLoading) return <InlineLoading label="Loading fuzz trials…" />;
  if (q.isError) {
    return <InlineError error={q.error} onRetry={() => q.refetch()} />;
  }
  const rows = q.data ?? [];
  if (rows.length === 0) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Fuzz trials ({rows.length})</CardTitle>
      </CardHeader>
      <CardContent className="p-0 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
            <tr>
              <th className="px-3 py-2 font-medium border-b">Scenario</th>
              <th className="px-3 py-2 font-medium border-b">Repeat</th>
              <th className="px-3 py-2 font-medium border-b">Trial</th>
              <th className="px-3 py-2 font-medium border-b">What</th>
              <th className="px-3 py-2 font-medium border-b">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.trial_id} className="border-b border-slate-100">
                <td className="px-3 py-2 align-top">
                  <div className="font-medium">{r.scenario_name ?? "—"}</div>
                  <div className="text-[10px] font-mono text-slate-500">
                    {r.scenario_key} [{r.parameter_key}]
                  </div>
                </td>
                <td className="px-3 py-2 font-mono text-xs text-slate-600">
                  {r.repeat_result_id.slice(-8)}
                </td>
                <td className="px-3 py-2 tabular-nums">{r.trial_index}</td>
                <td className="px-3 py-2 text-xs text-slate-700 max-w-md">
                  {r.summary_label || "—"}
                </td>
                <td className="px-3 py-2">
                  <Badge status={r.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
