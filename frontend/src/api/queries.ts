import { useQuery } from "@tanstack/react-query";
import type {
  CompareResponse,
  ExperimentSummary,
  FuzzTrialDetail,
  FuzzTrialRunRow,
  RepeatTrace,
  RunDetail,
  RunListPage,
  ScenarioRow,
} from "@/lib/types";
import { fetchJson } from "./http";

export const queryKeys = {
  experiments: ["experiments"] as const,
  runs: (params: {
    experiment_id?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }) => ["runs", params] as const,
  run: (id: string) => ["run", id] as const,
  scenarios: (runId: string) => ["scenarios", runId] as const,
  trace: (id: string) => ["trace", id] as const,
  compare: (ids: string[]) => ["compare", [...ids].sort().join(",")] as const,
  fuzzTrials: (runId: string) => ["fuzzTrials", runId] as const,
  fuzzTrial: (trialId: string) => ["fuzzTrial", trialId] as const,
};

export function useExperiments() {
  return useQuery<ExperimentSummary[]>({
    queryKey: queryKeys.experiments,
    queryFn: () => fetchJson("/api/experiments"),
  });
}

export function useRuns(params: {
  experiment_id?: string;
  status?: string;
  limit?: number;
  offset?: number;
} = {}) {
  const qs = new URLSearchParams();
  if (params.experiment_id) qs.set("experiment_id", params.experiment_id);
  if (params.status) qs.set("status", params.status);
  if (params.limit != null) qs.set("limit", String(params.limit));
  if (params.offset != null) qs.set("offset", String(params.offset));
  const url = `/api/runs${qs.size ? `?${qs.toString()}` : ""}`;
  return useQuery<RunListPage>({
    queryKey: queryKeys.runs(params),
    queryFn: () => fetchJson(url),
  });
}

export function useRun(runId: string | undefined) {
  return useQuery<RunDetail>({
    queryKey: runId ? queryKeys.run(runId) : ["run", "_none_"],
    queryFn: () => fetchJson<RunDetail>(`/api/runs/${runId}`),
    enabled: Boolean(runId),
  });
}

export function useScenariosForRun(runId: string | undefined) {
  return useQuery<ScenarioRow[]>({
    queryKey: runId ? queryKeys.scenarios(runId) : ["scenarios", "_none_"],
    queryFn: () => fetchJson<ScenarioRow[]>(`/api/runs/${runId}/scenarios`),
    enabled: Boolean(runId),
  });
}

export function useRepeatTrace(repeatId: string | undefined) {
  return useQuery<RepeatTrace>({
    queryKey: repeatId ? queryKeys.trace(repeatId) : ["trace", "_none_"],
    queryFn: () => fetchJson<RepeatTrace>(`/api/repeats/${repeatId}/trace`),
    enabled: Boolean(repeatId),
    staleTime: 60_000,
  });
}

export function useFuzzTrialsForRun(runId: string | undefined) {
  return useQuery<FuzzTrialRunRow[]>({
    queryKey: runId ? queryKeys.fuzzTrials(runId) : ["fuzzTrials", "_none_"],
    queryFn: () => fetchJson<FuzzTrialRunRow[]>(`/api/runs/${runId}/fuzz-trials`),
    enabled: Boolean(runId),
    staleTime: 30_000,
  });
}

export function useFuzzTrial(trialId: string | undefined) {
  return useQuery<FuzzTrialDetail>({
    queryKey: trialId ? queryKeys.fuzzTrial(trialId) : ["fuzzTrial", "_none_"],
    queryFn: () => fetchJson<FuzzTrialDetail>(`/api/fuzz-trials/${trialId}`),
    enabled: Boolean(trialId),
    staleTime: 30_000,
  });
}

export function useCompare(experimentIds: string[]) {
  const enabled = experimentIds.length >= 2;
  const qs = enabled
    ? `?experiments=${encodeURIComponent(experimentIds.join(","))}`
    : "";
  return useQuery<CompareResponse>({
    queryKey: queryKeys.compare(experimentIds),
    queryFn: () => fetchJson<CompareResponse>(`/api/compare${qs}`),
    enabled,
  });
}
