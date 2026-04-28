import { Columns3 } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";

export interface ColumnPickerOption {
  id: string;
  label: string;
  group?: string;
}

export function ColumnPicker({
  options,
  visibility,
  onToggle,
}: {
  options: ColumnPickerOption[];
  visibility: Record<string, boolean>;
  onToggle: (id: string, visible: boolean) => void;
}) {
  const groups = new Map<string, ColumnPickerOption[]>();
  for (const opt of options) {
    const key = opt.group ?? "Columns";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(opt);
  }
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm">
          <Columns3 className="h-4 w-4" /> Columns
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        {[...groups.entries()].map(([group, opts], i) => (
          <div key={group}>
            {i > 0 && <DropdownMenuSeparator />}
            <DropdownMenuLabel>{group}</DropdownMenuLabel>
            {opts.map((opt) => {
              const visible = visibility[opt.id] ?? true;
              return (
                <DropdownMenuCheckboxItem
                  key={opt.id}
                  checked={visible}
                  onCheckedChange={(v) => onToggle(opt.id, Boolean(v))}
                  onSelect={(e) => e.preventDefault()}
                >
                  {opt.label}
                </DropdownMenuCheckboxItem>
              );
            })}
          </div>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
