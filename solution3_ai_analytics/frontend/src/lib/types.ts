// Shared chat types — mirror the frozen Phase 2 SSE event contract.

export type StageName = "retrieve" | "generate" | "validate" | "execute" | "summarize";
export type StageStatus = "pending" | "running" | "done";

export interface StageState {
  status: StageStatus;
  detail?: string; // real fact reported by the backend for this step
}

export const STAGE_ORDER: StageName[] = [
  "retrieve", "generate", "validate", "execute", "summarize",
];

export const STAGE_LABELS: Record<StageName, string> = {
  retrieve: "Retrieving schema",
  generate: "Generating SQL",
  validate: "Validating & securing",
  execute: "Executing",
  summarize: "Summarizing",
};

export type ChartType = "bar" | "line" | "pie" | "donut" | "scatter" | "area" | "none";

export interface ChartSpec {
  type: ChartType;
  x_field?: string | null;
  y_field?: string | null;
  color_field?: string | null;
  title?: string | null;
}

export type Row = Record<string, unknown>;

export interface ChartData {
  chart_spec: ChartSpec;
  rows: Row[];
}

// Stored (unrendered) in Phase 3 — Phase 4's Behind-the-scenes panel consumes these.
export interface SqlData {
  sql_display: string;
  query_id: string;
  tenant_injected: boolean;
}
export interface AuditData {
  query_id: string;
  latency_ms: number | null;
  rows_returned: number;
  tables_used: string[];
}
export interface TrustChecks {
  access_validated: boolean;
  tenant_injected: boolean;
  read_only: boolean;
  audit_logged: boolean;
}
export interface TrustData {
  checks: TrustChecks;
  audit: AuditData;
}

// Full audit row from GET /audit/{query_id}.
export interface AuditRow {
  query_id: string;
  conversation_id: string;
  sponsor_id: string;
  sql: string;
  tables_used: string[];
  latency_ms: number;
  rows_returned: number;
  created_at: string;
}

export interface UserMessageT {
  id: string;
  role: "user";
  text: string;
}

export interface AIMessageT {
  id: string;
  role: "ai";
  stages: Record<StageName, StageState>;
  hasStages: boolean; // false on the presentation fast-path (no stage events)
  summary: string; // accumulated target text from token events
  chart?: ChartData;
  followups: string[];
  sql?: SqlData; // stored, NOT rendered in Phase 3
  trust?: TrustData; // stored, NOT rendered in Phase 3
  error?: string;
  done: boolean;
  // True once the first-arrival reveal animation has played. Persisted in the
  // conversation state so a later re-mount (panel close/reopen, scroll) renders
  // the final state instantly instead of replaying the animation.
  revealed: boolean;
}

export type ChatMessage = UserMessageT | AIMessageT;

export function emptyStages(): Record<StageName, StageState> {
  return {
    retrieve: { status: "pending" }, generate: { status: "pending" },
    validate: { status: "pending" }, execute: { status: "pending" },
    summarize: { status: "pending" },
  };
}
