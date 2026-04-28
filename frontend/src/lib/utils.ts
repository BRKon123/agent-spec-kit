import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDuration(ms: number | null | undefined): string {
  if (ms == null) return "—";
  if (ms < 1000) return `${ms}ms`;
  const s = ms / 1000;
  if (s < 60) return `${s.toFixed(2)}s`;
  const m = Math.floor(s / 60);
  const rs = Math.round(s - m * 60);
  return `${m}m ${rs}s`;
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

export function statusColor(
  status: string | null | undefined,
): { bg: string; text: string; border: string } {
  switch (status) {
    case "passed":
      return {
        bg: "bg-emerald-50",
        text: "text-emerald-700",
        border: "border-emerald-200",
      };
    case "failed":
      return { bg: "bg-rose-50", text: "text-rose-700", border: "border-rose-200" };
    case "error":
      return {
        bg: "bg-orange-50",
        text: "text-orange-700",
        border: "border-orange-200",
      };
    case "timeout":
      return {
        bg: "bg-amber-50",
        text: "text-amber-700",
        border: "border-amber-200",
      };
    case "skipped":
      return { bg: "bg-slate-50", text: "text-slate-600", border: "border-slate-200" };
    default:
      return { bg: "bg-slate-50", text: "text-slate-600", border: "border-slate-200" };
  }
}
