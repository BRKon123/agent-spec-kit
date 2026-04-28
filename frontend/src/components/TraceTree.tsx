import * as React from "react";
import { ChevronRight } from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { JsonView } from "@/components/JsonView";
import type { AgentEventNode } from "@/lib/types";
import { cn } from "@/lib/utils";

function shortRepr(v: unknown, max = 72): string {
  if (v == null) return "";
  let s: string;
  try {
    s = typeof v === "string" ? v : JSON.stringify(v);
  } catch {
    s = String(v);
  }
  if (s.length > max) return s.slice(0, max - 3) + "...";
  return s;
}

function nodeKind(node: AgentEventNode):
  | { kind: "tool"; label: string }
  | { kind: "agent_turn"; label: string }
  | { kind: "user_turn"; label: string }
  | { kind: "unknown"; label: string } {
  if (typeof node.tool_name === "string") {
    let suffix = "";
    if (node.error) {
      suffix = `error=${shortRepr(node.error)}`;
    } else if (node.result !== undefined && node.result !== null) {
      suffix = `result=${shortRepr(node.result)}`;
    } else {
      suffix = "(pending)";
    }
    return { kind: "tool", label: `${node.tool_name}  ${suffix}` };
  }
  if (node.content !== undefined) {
    const c = shortRepr(node.content);
    const e = node.error ? `  [error: ${shortRepr(node.error)}]` : "";
    return { kind: "user_turn", label: `UserTurn: ${c}${e}` };
  }
  if ("agent_output" in node || "user_input" in node) {
    const path =
      node.source_path && node.source_path.length
        ? node.source_path.join(".")
        : "root";
    return { kind: "agent_turn", label: `AgentTurn (${path})` };
  }
  return { kind: "unknown", label: "Event" };
}

function NodeBadge({ kind }: { kind: string }) {
  const palette: Record<string, string> = {
    tool: "bg-sky-50 text-sky-700 border-sky-200",
    agent_turn: "bg-violet-50 text-violet-700 border-violet-200",
    user_turn: "bg-emerald-50 text-emerald-700 border-emerald-200",
    unknown: "bg-slate-50 text-slate-600 border-slate-200",
  };
  const labels: Record<string, string> = {
    tool: "tool",
    agent_turn: "agent",
    user_turn: "user",
    unknown: "event",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-1.5 py-0.5 text-[10px] uppercase tracking-wide",
        palette[kind] ?? palette.unknown,
      )}
    >
      {labels[kind] ?? "event"}
    </span>
  );
}

function FieldToggle({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <Collapsible className="rounded-md border border-slate-200">
      <CollapsibleTrigger className="group flex w-full items-center gap-1.5 px-2 py-1 text-[11px] uppercase tracking-wide text-slate-600 hover:bg-slate-50">
        <ChevronRight className="h-3 w-3 transition-transform group-data-[state=open]:rotate-90" />
        {label}
      </CollapsibleTrigger>
      <CollapsibleContent className="px-2 py-2">{children}</CollapsibleContent>
    </Collapsible>
  );
}

function isPresent(v: unknown): boolean {
  if (v == null) return false;
  if (typeof v === "object" && Object.keys(v as object).length === 0) return false;
  if (typeof v === "string" && v.length === 0) return false;
  return true;
}

export function TraceNode({
  node,
  depth = 0,
  defaultOpen,
}: {
  node: AgentEventNode;
  depth?: number;
  defaultOpen?: boolean;
}) {
  const k = nodeKind(node);
  const fields: Array<[string, unknown]> = [];
  if (k.kind === "tool") {
    fields.push(["args", node.args]);
    fields.push(["result", node.result]);
    if (node.error) fields.push(["error", node.error]);
  } else if (k.kind === "agent_turn") {
    if ("user_input" in node) fields.push(["input", node.user_input]);
    if ("agent_output" in node) fields.push(["output", node.agent_output]);
    if (node.error) fields.push(["error", node.error]);
  } else if (k.kind === "user_turn") {
    fields.push(["content", node.content]);
    if (node.error) fields.push(["error", node.error]);
  }
  if (isPresent(node.metadata)) fields.push(["metadata", node.metadata]);

  const presentFields = fields.filter(([, v]) => isPresent(v));
  const children = node.children ?? [];
  const hasBody = presentFields.length > 0 || children.length > 0;

  return (
    <Collapsible
      defaultOpen={defaultOpen ?? depth === 0}
      className="border border-slate-200 rounded-md bg-white"
    >
      <CollapsibleTrigger
        className="flex w-full items-center gap-2 px-2 py-1.5 text-left hover:bg-slate-50 group"
        disabled={!hasBody}
      >
        <ChevronRight
          className={cn(
            "h-3.5 w-3.5 text-slate-400 transition-transform group-data-[state=open]:rotate-90",
            !hasBody && "opacity-0",
          )}
        />
        <NodeBadge kind={k.kind} />
        <span className="text-sm font-mono text-slate-800 truncate">
          {k.label}
        </span>
        {children.length > 0 && (
          <span className="ml-auto text-[10px] text-slate-400 tabular-nums">
            {children.length} child{children.length === 1 ? "" : "ren"}
          </span>
        )}
      </CollapsibleTrigger>
      {hasBody && (
        <CollapsibleContent>
          <div className="px-2 py-2 space-y-2">
            {presentFields.map(([label, value]) => (
              <FieldToggle key={label} label={label}>
                <JsonView value={value} />
              </FieldToggle>
            ))}
            {children.length > 0 && (
              <div className="pl-3 border-l border-slate-200 space-y-2">
                {children.map((child, i) => (
                  <TraceNode key={child.event_id ?? i} node={child} depth={depth + 1} />
                ))}
              </div>
            )}
          </div>
        </CollapsibleContent>
      )}
    </Collapsible>
  );
}

export function TraceTree({ roots }: { roots: AgentEventNode[][] | null }) {
  if (!roots || roots.length === 0) {
    return (
      <div className="text-xs text-slate-500">No event trace recorded.</div>
    );
  }
  return (
    <div className="space-y-3">
      {roots.map((groupOrNode, gi) => {
        // Each turn-group is an array of root events for that turn.
        const group = Array.isArray(groupOrNode) ? groupOrNode : [groupOrNode];
        return (
          <div key={gi} className="space-y-2">
            {roots.length > 1 && (
              <div className="text-[10px] uppercase tracking-wide text-slate-500">
                Turn {gi + 1}
              </div>
            )}
            {group.map((node, i) => (
              <TraceNode key={node.event_id ?? i} node={node} depth={0} />
            ))}
          </div>
        );
      })}
    </div>
  );
}
