// Typed API client (chassis). All URLs are built from the runtime base path (resolved from
// the URL, see lib/basepath.ts) so the app works at "/" or under "/apps/<slug>/" (Addendum
// A §A1) with no rebuild.
import { getBasePath } from "./lib/basepath";

// e.g. "/api" locally, "/apps/absorbance-lab/api" under AdaLab. The browser requests the
// prefixed URL; AdaLab strips the prefix before the backend sees "/api/...".
const API = getBasePath().replace(/\/$/, "") + "/api";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(API + path, {
    credentials: "same-origin",
    headers: opts.body ? { "Content-Type": "application/json" } : undefined,
    ...opts,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body && typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body?.detail)) detail = body.detail.map((d: any) => d.msg).join("; ");
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

// --- types -----------------------------------------------------------------
export interface JsonSchemaProp {
  type?: string;
  title?: string;
  description?: string;
  enum?: string[];
  format?: string;
  minimum?: number;
  maximum?: number;
  exclusiveMinimum?: number;
  exclusiveMaximum?: number;
  minLength?: number;
  maxLength?: number;
  anyOf?: JsonSchemaProp[];
  default?: unknown;
}

export interface JsonSchema {
  properties: Record<string, JsonSchemaProp>;
  required?: string[];
  title?: string;
}

export interface Meta {
  project_name: string;
  exercise_title: string;
  course_code: string;
  host_institution: string;
  institution_name: string;
  contact_email: string;
  open_cohort: string | null;
  admin_enabled: boolean;
  demo_mode: boolean;
  schema: JsonSchema;
  field_order: string[];
  numeric_fields: string[];
}

export interface Member {
  id: number;
  display_name: string;
}
export interface Group {
  id: number;
  name: string;
  cohort: string;
  members: Member[];
  created_at?: string;
}
export interface ResultRow {
  id: number;
  group_id: number;
  group: string;
  cohort: string;
  submitted_at: string;
  superseded: boolean;
  superseded_by: number | null;
  values: Record<string, unknown>;
}
export interface Cohort {
  id: number;
  label: string;
  status: string;
  created_at: string;
  closed_at: string | null;
  group_count: number;
  result_count: number;
}
export interface Analysis {
  cohort: string;
  chassis: Record<string, unknown>;
  exercise: Record<string, unknown> | null;
}

export type Payload = Record<string, unknown>;

// --- public ----------------------------------------------------------------
export const getMeta = () => req<Meta>("/meta");
export const getContent = () => req<{ markdown: string }>("/content");
export const listCohorts = () => req<Cohort[]>("/cohorts");
export const listGroups = (cohort?: string) =>
  req<Group[]>("/groups" + (cohort ? `?cohort=${encodeURIComponent(cohort)}` : ""));
export const createGroup = (name: string, members: string[]) =>
  req<Group>("/groups", { method: "POST", body: JSON.stringify({ name, members }) });
export const addMember = (groupId: number, display_name: string) =>
  req<Member>(`/groups/${groupId}/members`, { method: "POST", body: JSON.stringify({ display_name }) });
export const submitResult = (groupId: number, payload: Payload) =>
  req<{ id: number; values: Payload }>(`/groups/${groupId}/results`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const supersedeResult = (resultId: number, payload: Payload) =>
  req<{ id: number; values: Payload }>(`/results/${resultId}/supersede`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const getResults = (cohort: string, latest: boolean) =>
  req<ResultRow[]>(`/results?cohort=${encodeURIComponent(cohort)}&latest=${latest}`);
export const getAnalysis = (cohort: string) =>
  req<Analysis>(`/analysis?cohort=${encodeURIComponent(cohort)}`);

export function exportUrl(format: "csv" | "parquet", cohort: string, history: boolean): string {
  return `${API}/export?format=${format}&cohort=${encodeURIComponent(cohort)}&history=${history}`;
}

// --- admin -----------------------------------------------------------------
export const adminLogin = (password: string) =>
  req<{ ok: boolean }>("/admin/login", { method: "POST", body: JSON.stringify({ password }) });
export const adminLogout = () => req<{ ok: boolean }>("/admin/logout", { method: "POST" });
export const adminSession = () => req<{ ok: boolean }>("/admin/session");
export const adminListCohorts = () => req<Cohort[]>("/admin/cohorts");
export const adminOpenCohort = (label: string) =>
  req<Cohort>("/admin/cohorts", { method: "POST", body: JSON.stringify({ label }) });
export const adminCloseCohort = () => req<Cohort>("/admin/cohorts/close", { method: "POST" });
export const adminListGroups = (cohort: string) =>
  req<Group[]>(`/admin/groups?cohort=${encodeURIComponent(cohort)}`);
export const adminRenameGroup = (groupId: number, name: string) =>
  req<Group>(`/admin/groups/${groupId}`, { method: "PATCH", body: JSON.stringify({ name }) });
export const adminMergeGroups = (source_id: number, target_id: number) =>
  req<Group>("/admin/groups/merge", { method: "POST", body: JSON.stringify({ source_id, target_id }) });
export const adminDeleteGroup = (groupId: number) =>
  req<{ ok: boolean }>(`/admin/groups/${groupId}`, { method: "DELETE" });
export const adminDeleteMember = (memberId: number) =>
  req<{ ok: boolean }>(`/admin/members/${memberId}`, { method: "DELETE" });
export const adminDeleteResult = (resultId: number) =>
  req<{ ok: boolean }>(`/admin/results/${resultId}`, { method: "DELETE" });
export const adminSeedDemo = () =>
  req<{ ok: boolean; created_cohorts: string[] }>("/admin/demo/seed", { method: "POST" });
