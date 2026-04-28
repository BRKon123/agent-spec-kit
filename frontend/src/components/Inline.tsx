import { Button } from "@/components/ui/button";
import { ApiError } from "@/api/http";

export function InlineError({
  error,
  onRetry,
  className,
}: {
  error: unknown;
  onRetry?: () => void;
  className?: string;
}) {
  const problem =
    error instanceof ApiError
      ? error.problem
      : { title: "Unexpected error", detail: String(error), status: 0 };
  return (
    <div
      className={
        "rounded-md border border-rose-200 bg-rose-50 p-3 text-sm text-rose-900 " +
        (className ?? "")
      }
    >
      <div className="font-medium">{problem.title}</div>
      {problem.detail && <div className="text-xs mt-0.5 opacity-80">{problem.detail}</div>}
      {onRetry && (
        <div className="mt-2">
          <Button variant="outline" size="sm" onClick={onRetry}>
            Retry
          </Button>
        </div>
      )}
    </div>
  );
}

export function InlineLoading({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="text-sm text-slate-500 flex items-center gap-2 py-3">
      <span className="inline-block h-3 w-3 animate-pulse rounded-full bg-slate-300" />
      {label}
    </div>
  );
}

export function EmptyState({
  title,
  description,
}: {
  title: string;
  description?: string;
}) {
  return (
    <div className="rounded-md border border-dashed border-slate-200 bg-slate-50 p-6 text-center">
      <div className="text-sm font-medium text-slate-700">{title}</div>
      {description && (
        <div className="mt-1 text-xs text-slate-500">{description}</div>
      )}
    </div>
  );
}
