import { Fragment, useMemo, useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { FuzzTrialRunRow, ScenarioRow, RepeatSummary } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { formatDuration } from "@/lib/utils";

export interface ScenarioRepeatRow {
  scenario: ScenarioRow;
  repeat: RepeatSummary;
}

export function flattenScenarios(scenarios: ScenarioRow[]): ScenarioRepeatRow[] {
  const out: ScenarioRepeatRow[] = [];
  for (const s of scenarios) {
    if (!s.repeats || s.repeats.length === 0) {
      out.push({
        scenario: s,
        repeat: {
          repeat_result_id: "",
          repeat_index: 0,
          status: s.status,
          duration_ms: s.duration_ms ?? null,
          assertion_count: 0,
          assertion_passed: 0,
          failure_kind: null,
          failure_message: null,
        },
      });
      continue;
    }
    for (const r of s.repeats) out.push({ scenario: s, repeat: r });
  }
  return out;
}

export function collectParameterAxes(scenarios: ScenarioRow[]): string[] {
  const set = new Set<string>();
  for (const s of scenarios) {
    for (const k of Object.keys(s.parameters ?? {})) set.add(k);
  }
  return [...set].sort();
}

export interface ScenarioTableProps {
  scenarios: ScenarioRow[];
  fuzzTrials: FuzzTrialRunRow[];
  visibility: Record<string, boolean>;
  onScenarioRowClick?: (scenario: ScenarioRow) => void;
  onTrialRowClick: (trialId: string) => void;
}

export function ScenarioTable({
  scenarios,
  fuzzTrials,
  visibility,
  onScenarioRowClick,
  onTrialRowClick,
}: ScenarioTableProps) {
  const paramAxes = useMemo(() => collectParameterAxes(scenarios), [scenarios]);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const trialsByScenario = useMemo(() => {
    const m = new Map<string, FuzzTrialRunRow[]>();
    const scenarioKeyByRepeat = new Map<string, string>();
    for (const s of scenarios) {
      const sk = `${s.scenario_key}::${s.parameter_key}`;
      for (const r of s.repeats ?? []) {
        if (r.repeat_result_id) scenarioKeyByRepeat.set(r.repeat_result_id, sk);
      }
    }
    for (const t of fuzzTrials) {
      const key =
        scenarioKeyByRepeat.get(t.repeat_result_id) ??
        `${t.scenario_key ?? ""}::${t.parameter_key ?? ""}`;
      const arr = m.get(key);
      if (arr) arr.push(t);
      else m.set(key, [t]);
    }
    for (const arr of m.values()) arr.sort((a, b) => a.trial_index - b.trial_index);
    return m;
  }, [fuzzTrials]);

  const visibleColumns = useMemo(() => {
    const cols: Array<{ id: string; label: string }> = [];
    const push = (id: string, label: string) => {
      if (visibility[id] ?? true) cols.push({ id, label });
    };
    push("scenario_name", "Scenario");
    push("scenario_module", "Module");
    push("tags", "Tags");
    for (const axis of paramAxes) push(`param:${axis}`, axis);
    push("repeat", "Repeat");
    push("status", "Status");
    push("duration", "Duration");
    push("failure_kind", "Failure kind");
    push("failure_message", "Failure message");
    push("assertions", "Assertions");
    push("output_preview", "Output preview");
    return cols;
  }, [paramAxes, visibility]);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-2 py-2 border-b border-slate-200 w-28">Trials</th>
            {visibleColumns.map((c) => (
              <th key={c.id} className="px-3 py-2 font-medium border-b border-slate-200">
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {scenarios.map((s) => {
            const key = `${s.scenario_key}::${s.parameter_key}`;
            const trials = trialsByScenario.get(key) ?? [];
            const isExpanded = expanded[key] ?? false;
            const firstRepeat = s.repeats?.[0];
            return (
              <Fragment key={s.scenario_result_id}>
                <tr
                  onClick={() => onScenarioRowClick?.(s)}
                  className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer"
                >
                  <td className="px-2 py-2 align-top">
                    {trials.length > 0 ? (
                      <button
                        className="inline-flex items-center gap-1 rounded border border-slate-200 bg-white hover:bg-slate-100 px-1.5 py-1 text-xs text-slate-700"
                        onClick={(e) => {
                          e.stopPropagation();
                          setExpanded((prev) => ({ ...prev, [key]: !isExpanded }));
                        }}
                        title={isExpanded ? "Collapse trials" : "Expand trials"}
                      >
                        {isExpanded ? (
                          <ChevronDown className="h-4 w-4 text-slate-500" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-slate-500" />
                        )}
                        {trials.length}
                      </button>
                    ) : (
                      <span className="text-slate-300 text-xs">—</span>
                    )}
                  </td>
                  {visibleColumns.map((c) => (
                    <td key={c.id} className="px-3 py-2 align-top max-w-[28rem]">
                      {renderScenarioCell(c.id, s, firstRepeat, paramAxes)}
                    </td>
                  ))}
                </tr>
                {isExpanded && trials.length > 0 && (
                  <tr key={`${s.scenario_result_id}:trials`} className="border-b border-slate-100 bg-slate-50/40">
                    <td />
                    <td colSpan={visibleColumns.length} className="px-3 py-2">
                      <table className="w-full text-xs">
                        <thead className="text-slate-500">
                          <tr>
                            <th className="text-left py-1 px-2">Trial</th>
                            <th className="text-left py-1 px-2">Status</th>
                            <th className="text-left py-1 px-2">Summary</th>
                            <th className="text-left py-1 px-2">Failure</th>
                          </tr>
                        </thead>
                        <tbody>
                          {trials.map((t) => (
                            <tr
                              key={t.trial_id}
                              className="border-t border-slate-100 hover:bg-white cursor-pointer"
                              onClick={(e) => {
                                e.stopPropagation();
                                onTrialRowClick(t.trial_id);
                              }}
                            >
                              <td className="py-1.5 px-2 tabular-nums">#{t.trial_index}</td>
                              <td className="py-1.5 px-2">
                                <Badge status={t.status} />
                              </td>
                              <td className="py-1.5 px-2 text-slate-700">{t.summary_label || "—"}</td>
                              <td className="py-1.5 px-2 text-rose-700">
                                {t.failure_kind ?? t.failure_message ?? "—"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function renderScenarioCell(
  id: string,
  scenario: ScenarioRow,
  firstRepeat: RepeatSummary | undefined,
  _paramAxes: string[],
) {
  if (id === "scenario_name") return <div className="font-medium">{scenario.scenario_name}</div>;
  if (id === "scenario_module")
    return <span className="font-mono text-xs text-slate-500">{scenario.scenario_module ?? "—"}</span>;
  if (id === "tags") {
    return (
      <div className="flex flex-wrap gap-1">
        {scenario.tags.map((t) => (
          <span
            key={t}
            className="text-[10px] uppercase tracking-wide text-slate-600 bg-slate-100 rounded px-1 py-0.5"
          >
            {t}
          </span>
        ))}
      </div>
    );
  }
  if (id.startsWith("param:")) {
    const axis = id.slice("param:".length);
    return <span className="font-mono text-xs">{String(scenario.parameters[axis] ?? "—")}</span>;
  }
  if (id === "repeat")
    return (
      <span className="tabular-nums">
        {scenario.repeats_passed}/{scenario.repeats_total}
      </span>
    );
  if (id === "status") return <Badge status={scenario.status} />;
  if (id === "duration")
    return <span className="text-slate-600 tabular-nums">{formatDuration(scenario.duration_ms)}</span>;
  if (id === "failure_kind")
    return firstRepeat?.failure_kind ? (
      <span className="text-rose-700 text-xs">{firstRepeat.failure_kind}</span>
    ) : (
      <span className="text-slate-300">—</span>
    );
  if (id === "failure_message")
    return firstRepeat?.failure_message ? (
      <span className="text-xs text-rose-800/90 line-clamp-2">{firstRepeat.failure_message}</span>
    ) : (
      <span className="text-slate-300">—</span>
    );
  if (id === "assertions")
    return (
      <span className="tabular-nums text-slate-600">
        {firstRepeat?.assertion_passed ?? 0}/{firstRepeat?.assertion_count ?? 0}
      </span>
    );
  if (id === "output_preview")
    return <span className="text-xs text-slate-500 line-clamp-2">{firstRepeat?.output_preview ?? "—"}</span>;
  return <span className="text-slate-300">—</span>;
}
