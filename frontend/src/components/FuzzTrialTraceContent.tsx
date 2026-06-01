import type { AgentEventNode, FuzzTrialDetail } from "@/lib/types";
import { TraceTree } from "@/components/TraceTree";
import { FailureCard } from "@/components/FailureCard";
import { JsonView } from "@/components/JsonView";

export function FuzzTrialTraceContent({ trial }: { trial: FuzzTrialDetail }) {
  return (
    <>
      {trial.user_turns?.length > 0 && (
        <section>
          <h3 className="text-sm font-semibold mb-2">User turns</h3>
          <ol className="list-decimal list-inside space-y-1 text-sm">
            {trial.user_turns.map((u, i) => (
              <li key={i} className="whitespace-pre-wrap break-words">
                {u}
              </li>
            ))}
          </ol>
        </section>
      )}

      <section>
        <h3 className="text-sm font-semibold mb-2">Event trace</h3>
        <TraceTree
          transcript={trial.transcript}
          roots={
            trial.status !== "passed" &&
            Array.isArray(trial.counterexample?.events) &&
            (trial.counterexample?.events?.length ?? 0) > 0
              ? (trial.counterexample!.events as AgentEventNode[])
              : null
          }
        />
        {Object.keys(trial.blob_errors ?? {}).length > 0 && (
          <div className="mt-2">
            <div className="text-[11px] uppercase tracking-wide text-slate-500 mb-1">
              Blob errors
            </div>
            <JsonView value={trial.blob_errors} />
          </div>
        )}
      </section>

      {(trial.status !== "passed" || trial.failure_message || trial.failure_kind) && (
        <section>
          <h3 className="text-sm font-semibold mb-2">Failure</h3>
          <FailureCard
            counterexample={trial.counterexample ?? null}
            rawError={trial.raw_error ?? null}
            blobErrors={trial.blob_errors ?? {}}
            failureMessage={trial.failure_message ?? null}
            assertionType={trial.failure_kind ?? null}
          />
        </section>
      )}
    </>
  );
}
