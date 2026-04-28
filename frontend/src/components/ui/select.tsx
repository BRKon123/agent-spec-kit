import * as React from "react";
import { cn } from "@/lib/utils";

export const Select = React.forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement>
>(({ className, ...props }, ref) => (
  <select
    ref={ref}
    className={cn(
      "h-9 rounded-md border border-slate-200 bg-white px-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-300",
      className,
    )}
    {...props}
  />
));
Select.displayName = "Select";
