import * as React from "react";
import { ChevronRight } from "lucide-react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { JsonView } from "@/components/JsonView";
import type { AgentEventNode, ConversationTurn } from "@/lib/types";
import { cn } from "@/lib/utils";

const FIELD_SCROLL_CLASS = "max-h-[min(50vh,28rem)]";

function shortRepr(v: unknown, max = 120): string {
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
  | { kind: "tool"; label: string; title: string }
  | { kind: "agent_turn"; label: string; title: string }
  | { kind: "user_turn"; label: string; title: string }
  | { kind: "unknown"; label: string; title: string } {
  if (typeof node.tool_name === "string") {
    let suffix = "";
    if (node.error) {
      suffix = `error=${shortRepr(node.error, 200)}`;
    } else if (node.result !== undefined && node.result !== null) {
      suffix = `result=${shortRepr(node.result, 200)}`;
    } else {
      suffix = "(pending)";
    }
    const title = `${node.tool_name}  ${suffix}`;
    return { kind: "tool", label: title, title };
  }
  if (node.content !== undefined) {
    const c = shortRepr(node.content, 200);
    const e = node.error ? `  [error: ${shortRepr(node.error, 400)}]` : "";
    const title = `UserTurn: ${c}${e}`;
    return { kind: "user_turn", label: title, title };
  }
  if ("agent_output" in node || "user_input" in node) {
    const path = node.source_path && node.source_path.length
      ? node.source_path.join(".")
      : "";
    const o = shortRepr(node.agent_output, 200);
    const e = node.error ? `  [error: ${shortRepr(node.error, 400)}]` : "";
    const prefix = path ? `AgentTurn (${path})` : "AgentTurn";
    const title = `${prefix}: ${o}${e}`;
    return { kind: "agent_turn", label: title, title };
  }
  return { kind: "unknown", label: "Event", title: "Event" };
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
        "inline-flex items-center rounded-full border px-1.5 py-0.5 text-[10px] uppercase tracking-wide shrink-0",
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
        <ChevronRight className="h-3 w-3 shrink-0 transition-transform group-data-[state=open]:rotate-90" />
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

function agentNodesFromTurn(turn: ConversationTurn): AgentEventNode[] {
  const ev = turn.events ?? [];
  if (ev.length > 0) {
    return ev;
  }
  if (turn.error != null || isPresent(turn.output)) {
    return [
      {
        agent_output: turn.output ?? null,
        error: turn.error ?? null,
        children: [],
      },
    ];
  }
  return [];
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
  const openByDefault =
    defaultOpen ?? (depth === 0 && Boolean(node.error) && k.kind === "agent_turn");

  return (
    <Collapsible
      defaultOpen={openByDefault}
      className="border border-slate-200 rounded-md bg-white"
    >
      <CollapsibleTrigger
        className="flex w-full items-start gap-2 px-2 py-1.5 text-left hover:bg-slate-50 group"
        disabled={!hasBody}
      >
        <ChevronRight
          className={cn(
            "h-3.5 w-3.5 text-slate-400 shrink-0 mt-0.5 transition-transform group-data-[state=open]:rotate-90",
            !hasBody && "opacity-0",
          )}
        />
        <NodeBadge kind={k.kind} />
        <span
          className="text-sm font-mono text-slate-800 min-w-0 flex-1 line-clamp-2 break-all"
          title={k.title}
        >
          {k.label}
        </span>
        {children.length > 0 && (
          <span className="text-[10px] text-slate-400 tabular-nums shrink-0">
            {children.length} child{children.length === 1 ? "" : "ren"}
          </span>
        )}
      </CollapsibleTrigger>
      {hasBody && (
        <CollapsibleContent>
          <div className="px-2 py-2 space-y-2">
            {children.length > 0 && (
              <div className="pl-3 border-l border-slate-200 space-y-2">
                {children.map((child, i) => (
                  <TraceNode key={child.event_id ?? i} node={child} depth={depth + 1} />
                ))}
              </div>
            )}
            {presentFields.map(([label, value]) => (
              <FieldToggle key={label} label={label}>
                <JsonView value={value} maxHeightClass={FIELD_SCROLL_CLASS} />
              </FieldToggle>
            ))}
          </div>
        </CollapsibleContent>
      )}
    </Collapsible>
  );
}

function isRootAgentTurnShell(node: AgentEventNode): boolean {
  if (typeof node.tool_name === "string") return false;
  const hasTurnFields = "agent_output" in node || "user_input" in node;
  if (!hasTurnFields) return false;
  const sp = node.source_path;
  return !sp || sp.length === 0;
}

function flattenRootAgentShells(nodes: AgentEventNode[]): AgentEventNode[] {
  const out: AgentEventNode[] = [];
  for (const n of nodes) {
    if (isRootAgentTurnShell(n)) {
      out.push(...flattenRootAgentShells(n.children ?? []));
    } else {
      out.push(n);
    }
  }
  return out;
}

function flattenUserChildren(events: AgentEventNode[]): AgentEventNode[] {
  if (events.length === 1 && isRootAgentTurnShell(events[0])) {
    return flattenRootAgentShells(events[0].children ?? []);
  }
  return events;
}

function TraceRoots({ roots }: { roots: AgentEventNode[] }) {
  return (
    <div className="space-y-2">
      {roots.map((node, i) => (
        <TraceNode key={node.event_id ?? i} node={node} depth={0} />
      ))}
    </div>
  );
}

export function TraceTree({
  transcript,
  roots,
}: {
  transcript: ConversationTurn[] | null;
  /** Flat event roots (e.g. counterexample.events); used when richer than transcript. */
  roots?: AgentEventNode[] | null;
}) {
  if (roots && roots.length > 0) {
    return <TraceRoots roots={roots} />;
  }

  if (!transcript || transcript.length === 0) {
    return (
      <div className="text-xs text-slate-500">No event trace recorded.</div>
    );
  }

  const showHeaders = transcript.length > 1;
  return (
    <div className="space-y-3">
      {transcript.map((turn, ti) => {
        let nodes: AgentEventNode[];
        if (turn.actor === "user") {
          const userNode: AgentEventNode = {
            content: turn.output,
            error: turn.error ?? null,
            children: flattenUserChildren(turn.events ?? []),
          };
          nodes = [userNode];
        } else {
          nodes = agentNodesFromTurn(turn);
        }
        return (
          <div key={ti} className="space-y-2">
            {showHeaders && (
              <div className="text-[10px] uppercase tracking-wide text-slate-500">
                Turn {ti + 1} — {turn.actor}
              </div>
            )}
            {nodes.length === 0 ? (
              <div className="text-xs text-slate-400 italic px-2">
                (no events recorded for this turn)
              </div>
            ) : (
              nodes.map((node, i) => (
                <TraceNode
                  key={node.event_id ?? i}
                  node={node}
                  depth={0}
                />
              ))
            )}
          </div>
        );
      })}
    </div>
  );
}