export type Status = "passed" | "failed" | "error" | "timeout" | "skipped";

export interface ProblemDetail {
  type: string;
  title: string;
  status: number;
  detail?: string | null;
  instance?: string | null;
}

export interface ExperimentSummary {
  experiment_id: string;
  name: string;
  created_at?: string | null;
  run_count: number;
  last_run_at?: string | null;
  last_run_status?: Status | null;
  last_run_id?: string | null;
}

export interface RunListItem {
  run_id: string;
  experiment_id: string;
  experiment_name: string;
  status: Status;
  started_at: string;
  finished_at?: string | null;
  scenario_passed: number;
  scenario_count: number;
  scenario_failed: number;
  repeat_pass_rate: number;
  mean_duration_ms: number;
  summary: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export interface RunDetail {
  run_id: string;
  experiment_id?: string | null;
  experiment_name: string;
  status: Status;
  started_at: string;
  finished_at?: string | null;
  command?: string | null;
  notes?: string | null;
  git_commit?: string | null;
  git_branch?: string | null;
  git_dirty?: boolean | null;
  python_version?: string | null;
  package_version?: string | null;
  summary: Record<string, unknown>;
  metadata: Record<string, unknown>;
}

export interface RepeatSummary {
  repeat_result_id: string;
  repeat_index: number;
  status: Status;
  started_at?: string | null;
  finished_at?: string | null;
  duration_ms?: number | null;
  output_preview?: string | null;
  failure_kind?: string | null;
  failure_message?: string | null;
  assertion_count: number;
  assertion_passed: number;
}

export interface ScenarioRow {
  scenario_result_id: string;
  run_id: string;
  scenario_name: string;
  scenario_module?: string | null;
  scenario_file?: string | null;
  scenario_key: string;
  parameter_key: string;
  parameters: Record<string, unknown>;
  tags: string[];
  status: Status;
  repeats_total: number;
  repeats_passed: number;
  repeats_failed: number;
  duration_ms?: number | null;
  summary: Record<string, unknown>;
  repeats: RepeatSummary[];
}

export interface AssertionRow {
  assertion_id: string;
  assertion_type: string;
  actor?: string | null;
  turn_index?: number | null;
  status: Status;
  message?: string | null;
  details: Record<string, unknown>;
  counterexample_blob_path?: string | null;
}

export interface AgentEventNode {
  turn_index?: number | null;
  event_id?: string | null;
  source_path?: (string | number)[];
  metadata?: Record<string, unknown>;
  children?: AgentEventNode[];
  // ToolCallEvent
  tool_name?: string;
  args?: unknown;
  result?: unknown;
  error?: string | null;
  // AgentTurnEvent
  user_input?: unknown;
  agent_output?: unknown;
  // UserTurnEvent
  content?: unknown;
}

export interface ConversationTurn {
  actor: "user" | "agent";
  output: unknown;
  events: AgentEventNode[];
  status?: string;
  error?: string | null;
}

export interface Counterexample {
  headline: string;
  location: string;
  path?: string | null;
  expected_summary: string;
  actual_min: unknown;
  notes?: string[];
  check_kind?: string | null;
  location_detail?: string | null;
  events?: AgentEventNode[];
}

export interface PhaseErrorRow {
  phase_error_id: string;
  repeat_result_id: string;
  phase: "fuzz" | "shrink" | "extract";
  sub_phase?: string | null;
  error_kind: string;
  message: string;
  traceback_blob_path?: string | null;
  occurred_at: string;
}

export interface FuzzTrialSummary {
  trial_id: string;
  repeat_result_id: string;
  trial_index: number;
  seed?: number | null;
  status: Status;
  summary_label?: string;
  failure_kind?: string | null;
  failure_message?: string | null;
}

export interface FuzzTrialRunRow extends FuzzTrialSummary {
  user_turns: string[];
  behaviour_labels: string[];
  behaviour_details: Record<string, unknown>[];
  failure_signature?: Record<string, unknown> | null;
  started_at?: string | null;
  finished_at?: string | null;
  duration_ms?: number | null;
  transcript_blob_path?: string | null;
  scenario_key?: string;
  parameter_key?: string;
  scenario_name?: string;
}

export interface FuzzTrialDetail extends FuzzTrialRunRow {
  transcript: ConversationTurn[] | null;
  counterexample: Counterexample | null;
  raw_error: { error: string } | null;
  blob_errors: Record<string, string>;
}

export interface RepeatTrace {
  repeat_result_id: string;
  scenario_result_id: string;
  run_id: string;
  scenario_name: string;
  scenario_module?: string | null;
  scenario_key: string;
  parameter_key: string;
  parameters: Record<string, unknown>;
  tags: string[];
  repeat_index: number;
  status: Status;
  started_at?: string | null;
  finished_at?: string | null;
  duration_ms?: number | null;
  output_preview?: string | null;
  failure_kind?: string | null;
  failure_message?: string | null;
  assertions: AssertionRow[];
  transcript: ConversationTurn[] | null;
  counterexample: Counterexample | null;
  raw_error: { error: string } | null;
  blob_errors: Record<string, string>;
  phase_errors?: PhaseErrorRow[];
  fuzz_trials?: FuzzTrialSummary[];
}

export interface CompareCellLatestRepeat {
  repeat_result_id: string;
  repeat_index: number;
  status: Status;
  duration_ms?: number | null;
  failure_kind?: string | null;
  failure_message?: string | null;
}

export interface CompareCell {
  scenario_result_id: string;
  run_id: string;
  scenario_status: Status;
  scenario_duration_ms?: number | null;
  repeats_passed: number;
  repeats_failed: number;
  repeats_total: number;
  latest_repeat: CompareCellLatestRepeat | null;
}

export interface CompareRow {
  scenario_key: string;
  parameter_key: string;
  scenario_name: string;
  parameters: Record<string, unknown>;
  tags: string[];
  cells: Record<string, CompareCell | null>;
}

export interface CompareExperimentMeta {
  experiment_id: string;
  name: string;
  latest_run_id?: string | null;
  latest_run_started_at?: string | null;
}

export interface CompareResponse {
  experiments: CompareExperimentMeta[];
  rows: CompareRow[];
  excluded_fuzz_scenarios?: { scenario_key: string; parameter_key: string; scenario_name: string }[];
}
