import { useEffect, useState } from "react";

export function useStoredColumnVisibility(
  storageKey: string,
  defaults: Record<string, boolean>,
): [Record<string, boolean>, (next: Record<string, boolean>) => void] {
  const [state, setState] = useState<Record<string, boolean>>(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) return defaults;
      const parsed = JSON.parse(raw) as Record<string, boolean>;
      return { ...defaults, ...parsed };
    } catch {
      return defaults;
    }
  });
  useEffect(() => {
    try {
      localStorage.setItem(storageKey, JSON.stringify(state));
    } catch {
      // ignore quota errors
    }
  }, [state, storageKey]);
  return [state, setState];
}
