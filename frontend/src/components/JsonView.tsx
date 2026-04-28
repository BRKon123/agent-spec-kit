import { cn } from "@/lib/utils";

export function JsonView({
  value,
  className,
}: {
  value: unknown;
  className?: string;
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
  return (
    <pre
      className={cn(
        "rounded-md bg-slate-50 border border-slate-200 px-3 py-2 text-xs leading-relaxed font-mono whitespace-pre-wrap break-words max-h-[40vh] overflow-auto",
        className,
      )}
    >
      {body}
    </pre>
  );
}
