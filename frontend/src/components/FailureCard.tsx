import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { JsonView } from "@/components/JsonView";
import type { Counterexample } from "@/lib/types";

export function FailureCard({
  counterexample,
  rawError,
  blobErrors,
  failureMessage,
  assertionType,
}: {
  counterexample: Counterexample | null;
  rawError: { error: string } | null;
  blobErrors: Record<string, string>;
  failureMessage?: string | null;
  assertionType?: string | null;
}) {
  const cx = counterexample;
  return (
    <Card className="border-rose-200 bg-rose-50/40">
      <CardHeader className="border-rose-200 bg-rose-50/70">
        <CardTitle className="text-sm text-rose-900">
          {assertionType ?? cx?.headline ?? failureMessage ?? "Failure"}
        </CardTitle>
        {cx?.location_detail && (
          <p className="text-xs text-rose-800/80">{cx.location_detail}</p>
        )}
      </CardHeader>
      <CardContent className="text-xs space-y-3">
        {cx ? (
          <>
            {cx.check_kind && (
              <KV k="Check" v={<span className="font-mono">{cx.check_kind}</span>} />
            )}
            <KV k="Where" v={cx.location_detail ?? cx.location} />
            {cx.path && cx.path !== "$" && (
              <KV k="Path" v={<span className="font-mono">{cx.path}</span>} />
            )}
            <KV k="Expected" v={<span>{cx.expected_summary}</span>} />
            <div>
              <div className="text-[11px] uppercase tracking-wide text-rose-800/80 mb-1">
                Actual
              </div>
              <JsonView
                value={cx.actual_min}
                className="bg-white border-rose-200"
              />
            </div>
            {cx.notes && cx.notes.length > 0 && (
              <div>
                <div className="text-[11px] uppercase tracking-wide text-rose-800/80 mb-1">
                  Notes
                </div>
                <ul className="list-disc list-inside space-y-1">
                  {cx.notes.map((n, i) => (
                    <li key={i} className="text-rose-900/90 whitespace-pre-wrap">
                      {n}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </>
        ) : (
          failureMessage && (
            <div className="text-rose-900 whitespace-pre-wrap">{failureMessage}</div>
          )
        )}
        {rawError?.error && (
          <div>
            <div className="text-[11px] uppercase tracking-wide text-rose-800/80 mb-1">
              Raw error
            </div>
            <JsonView value={rawError.error} className="bg-white border-rose-200" />
          </div>
        )}
        {Object.keys(blobErrors).length > 0 && (
          <div className="text-[11px] text-rose-800/80">
            <div className="font-medium mb-1">Trace data unavailable for:</div>
            <ul className="list-disc list-inside">
              {Object.entries(blobErrors).map(([k, v]) => (
                <li key={k}>
                  <span className="font-mono">{k}</span>: {v}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function KV({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex gap-2">
      <div className="w-20 shrink-0 text-rose-700">{k}</div>
      <div className="flex-1 break-words text-rose-900">{v}</div>
    </div>
  );
}
