import * as React from "react";
import { cn, statusColor } from "@/lib/utils";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  status?: string | null;
}

export const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, status, children, ...props }, ref) => {
    const c = statusColor(status);
    return (
      <span
        ref={ref}
        className={cn(
          "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium",
          c.bg,
          c.text,
          c.border,
          className,
        )}
        {...props}
      >
        {children ?? status ?? "—"}
      </span>
    );
  },
);
Badge.displayName = "Badge";
