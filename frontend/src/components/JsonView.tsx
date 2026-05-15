import { cn } from "@/lib/utils";

export function JsonView({
  value,
  className,
  maxHeightClass = "max-h-[40vh]",
  scrollable = false,
}: {
  value: unknown;
  className?: string;
  /** Tailwind max-height utility; use a larger value or `max-h-none` in failure panels. */
  maxHeightClass?: string;
  /** When true, wrap content in a bounded scroll container (use in flex / dialog layouts). */
  scrollable?: boolean;
}) {
  if (value == null) {
    return <span className="text-xs text-slate-400">null</span>;
  }
  let body: string;
  try {
    body = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  } catch {
    body = String(value);
  }
  const pre = (
    <pre className="p-3 text-xs leading-relaxed font-mono whitespace-pre">
      {body}
    </pre>
  );
  if (scrollable) {
    return (
      <div
        className={cn(
          "min-h-0 overflow-auto overflow-x-auto rounded-md border border-slate-200 bg-slate-50",
          maxHeightClass,
          className,
        )}
      >
        {pre}
      </div>
    );
  }
  return (
    <pre
      className={cn(
        "rounded-md bg-slate-50 border border-slate-200 px-3 py-2 text-xs leading-relaxed font-mono whitespace-pre-wrap break-words",
        className,
      )}
    >
      {body}
    </pre>
  );
}
