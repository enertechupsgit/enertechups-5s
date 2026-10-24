import type {
  Plant,
  Zone,
  ZoneCreatePayload,
  ZoneUpdatePayload,
  Activity,
  RedTag,
  AuditRun,
  DashboardStats,
  ActivityComment,
  ZonalLeader,
  ZonalLeaderCreatePayload,
  ZonalLeaderUpdatePayload,
  ReportSubmissionPayload,
  ReportReviewPayload,
} from "../types";

export const BASE_URL = import.meta.env.VITE_API_URL || "/api/v1";
let connected = false;
export async function request<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-Workspace-Request": "1",
      ...options?.headers,
    },
    signal: options?.signal || AbortSignal.timeout(15000),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(
      typeof body?.detail === "string"
        ? body.detail
        : `Request failed (${response.status}). Please check your input and try again.`,
    );
  }
  connected = true;
  if (response.status === 204) return undefined as T;
  return response.json();
}
const query = (values: Record<string, unknown>) =>
  new URLSearchParams(
    Object.entries(values)
      .filter(([, v]) => v !== undefined && v !== "")
      .map(([k, v]) => [k, String(v)]),
  ).toString();
const write = <T>(path: string, method: string, body?: unknown) =>
  request<T>(path, {
    method,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
export async function checkBackendConnection() {
  try {
    connected = (
      await fetch(BASE_URL.replace(/\/api\/v1\/?$/, "/health"), {
        signal: AbortSignal.timeout(3000),
      })
    ).ok;
  } catch {
    connected = false;
  }
  return connected;
}
export const getIsLiveApi = () => connected;
export interface WorkspaceIdentity {
  id: string;
  name: string;
  first_name: string;
  last_name: string;
  email: string;
  role: "director" | "supervisor" | "auditor" | "zonal_leader" | "hr" | "admin";
  plant_id: string;
  zone_id: string | null;
  zone_name: string | null;
  permissions: string[];
}
export const fetchLocalIdentities = () =>
  request<WorkspaceIdentity[]>("/auth/local-identities");
export const fetchIdentity = () => request<WorkspaceIdentity>("/auth/me");
export const switchIdentity = (profileId: string) =>
  write<WorkspaceIdentity>("/auth/local-session", "POST", {
    profile_id: profileId,
  });
export const logout = () => write("/auth/logout", "POST");
export const fetchPlants = () => request<Plant[]>("/plants");
export const fetchZones = (deptId?: string) =>
  request<Zone[]>(`/plants/zones?${query({ dept_id: deptId })}`);
export const createZone = (payload: ZoneCreatePayload) =>
  write<Zone>("/plants/zones", "POST", payload);
export const updateZone = (id: string, payload: ZoneUpdatePayload) =>
  write<Zone>(`/plants/zones/${id}`, "PUT", payload);
export const deleteZone = async (id: string) => {
  await write(`/plants/zones/${id}`, "DELETE");
};
export const fetchPlantDashboard = (id: string) =>
  request<DashboardStats>(`/plants/${id}/dashboard`);
export const fetchActivities = (filters?: {
  plant_id?: string;
  zone_id?: string;
  status?: string;
  category?: string;
  priority?: string;
}) => request<Activity[]>(`/activities?${query(filters || {})}`);
export const createActivity = (
  payload: Partial<Activity> & { initial_before_photo_url?: string },
) => write<Activity>("/activities", "POST", payload);
export const startActivity = (id: string) =>
  write<Activity>(`/activities/${id}/start`, "POST");
export const submitActivityReport = (payload: ReportSubmissionPayload) =>
  write<Activity>(`/activities/${payload.activity_id}/report`, "POST", payload);
export const submitActivityForReview = (
  id: string,
  payload: Omit<ReportSubmissionPayload, "activity_id" | "after_photo_url"> & {
    after_photo_url?: string;
  },
) => write<Activity>(`/activities/${id}/report`, "POST", payload);
export const reviewActivityReport = (
  id: string,
  payload: ReportReviewPayload,
) => write<Activity>(`/activities/${id}/review`, "POST", payload);
export const reviewActivityDecision = (
  id: string,
  payload: {
    decision: "approved" | "rejected";
    rejection_reason?: string;
    supervisor_note?: string;
  },
) =>
  write<Activity>(`/activities/${id}/review`, "POST", {
    decision: payload.decision === "approved" ? "approve" : "reject",
    rejection_reason: payload.rejection_reason,
    review_notes: payload.supervisor_note,
  });
export const addActivityComment = (
  id: string,
  comment: string,
  authorName = "Local operator",
) =>
  write<ActivityComment>(`/activities/${id}/comments`, "POST", {
    comment,
    author_name: authorName,
  });
export const fetchRedTags = (filters?: {
  plant_id?: string;
  zone_id?: string;
  is_closed?: boolean;
}) => request<RedTag[]>(`/redtags?${query(filters || {})}`);
export const createRedTag = (payload: {
  plant_id: string;
  zone_id: string;
  item_name: string;
  item_category: string;
  quantity: number;
  reason: string;
  photo_url?: string;
  logged_by_name?: string;
}) => write<RedTag>("/redtags", "POST", payload);
export const updateRedTagDisposition = (
  id: string,
  payload: {
    disposition:
      "relocate" | "scrap" | "return_to_vendor" | "hold_for_evaluation";
    disposition_notes: string;
    is_closed: boolean;
  },
) => write<RedTag>(`/redtags/${id}/disposition`, "PUT", payload);
export const fetchAudits = (plantId?: string, zoneId?: string) =>
  request<AuditRun[]>(
    `/audits?${query({ plant_id: plantId, zone_id: zoneId })}`,
  );
export const submitAudit = (payload: {
  plant_id: string;
  zone_id: string;
  zone_name: string;
  auditor_name: string;
  sort_score: number;
  set_in_order_score: number;
  shine_score: number;
  standardize_score: number;
  sustain_score: number;
  notes?: string;
}) => write<AuditRun>("/audits", "POST", payload);
export const getActivityPdfDownloadUrl = (id: string) =>
  `${BASE_URL}/reports/activity/${id}/pdf`;
export const fetchZonalLeaders = (plantId?: string) =>
  request<ZonalLeader[]>(
    `/management/zonal-leaders?${query({ plant_id: plantId })}`,
  );
export const createZonalLeader = (payload: ZonalLeaderCreatePayload) =>
  write<ZonalLeader>("/management/zonal-leaders", "POST", payload);
export const updateZonalLeader = (
  id: string,
  payload: ZonalLeaderUpdatePayload,
) => write<ZonalLeader>(`/management/zonal-leaders/${id}`, "PUT", payload);
export const deleteZonalLeader = async (id: string) => {
  await write(`/management/zonal-leaders/${id}`, "DELETE");
};
export interface AssetRecord {
  id: string;
  plant_id: string;
  zone_id: string | null;
  parent_id: string | null;
  name: string;
  code: string;
  description: string | null;
  status: string;
  manufacturer: string | null;
  model: string | null;
  created_at: string;
  events: { id: string; status: string; note: string; created_at: string }[];
}
export const fetchAssets = (plantId: string) =>
  request<AssetRecord[]>(`/assets?${query({ plant_id: plantId })}`);
export const saveAsset = (payload: Partial<AssetRecord>) =>
  write<AssetRecord>("/assets", "POST", payload);
export const setAssetStatus = (id: string, status: string, note: string) =>
  write<AssetRecord>(`/assets/${id}/status`, "POST", { status, note });
