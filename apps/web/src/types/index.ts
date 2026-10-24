export type FiveSCategory =
  | "sort_seiri"
  | "set_in_order_seiton"
  | "shine_seiso"
  | "standardize_seiketsu"
  | "sustain_shitsuke";

export type ActivityStatus =
  | "draft"
  | "assigned"
  | "in_progress"
  | "submitted_for_review"
  | "approved"
  | "rejected"
  | "completed";

export type PriorityLevel = "low" | "medium" | "high" | "critical";

export type MediaType =
  "before_photo" | "after_photo" | "action_step" | "supporting_doc";

export type RedTagDisposition =
  "pending" | "relocate" | "scrap" | "return_to_vendor" | "hold_for_evaluation";

export type UserRole =
  | "operator"
  | "supervisor"
  | "auditor"
  | "plant_manager"
  | "management"
  | "zonal_leader";

export interface ZonalLeader {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone_number?: string | null;
  role: string;
  plant_id: string;
  dept_id?: string | null;
  assigned_zone_id?: string | null;
  assigned_zone_name?: string | null;
  avatar_url?: string;
  is_active: boolean;
  active_tasks_count: number;
  completed_tasks_count: number;
  created_at: string;
}

export interface ZonalLeaderCreatePayload {
  first_name: string;
  last_name: string;
  email: string;
  phone_number?: string;
  plant_id: string;
  assigned_zone_id?: string | null;
  role?: string;
}

export interface ZonalLeaderUpdatePayload {
  first_name?: string;
  last_name?: string;
  email?: string;
  phone_number?: string;
  assigned_zone_id?: string | null;
  role?: string;
  is_active?: boolean;
}

export interface ReportSubmissionPayload {
  activity_id: string;
  title?: string;
  corrective_action: string;
  outcome_description?: string;
  after_photo_url: string;
  before_photo_url?: string;
  benefits_safety?: boolean;
  benefits_space_sqft?: number;
  benefits_time_seconds?: number;
  benefits_cost_savings?: number;
  benefits_summary?: string;
}

export interface ReportReviewPayload {
  decision: "approve" | "reject";
  rejection_reason?: string;
}

export interface UserPersona {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  roleTitle: string;
  avatar: string;
  deptId?: string;
  deptName?: string;
  assignedZoneId?: string;
  assignedZoneName?: string;
  canApproveKaizen: boolean;
  canExecuteAudit: boolean;
  canDisposeRedTag: boolean;
  canViewAllZones: boolean;
  description: string;
}

export interface EvidenceMedia {
  id: string;
  activity_id: string;
  media_type: MediaType;
  file_name: string;
  file_url: string;
  file_size_bytes?: number;
  mime_type?: string;
  annotations_json?: any;
  created_at: string;
}

export interface ActivityHistory {
  actor_id?: string | null;
  id: string;
  activity_id: string;
  actor_name?: string;
  from_status?: string | null;
  to_status: string;
  action_note?: string;
  created_at: string;
}

export interface ActivityComment {
  attachments?: string[];
  id: string;
  activity_id: string;
  author_name: string;
  comment: string;
  is_internal?: boolean;
  created_at: string;
}

export interface Activity {
  id: string;
  activity_number: string;
  plant_id: string;
  zone_id: string;
  category: FiveSCategory;
  title: string;
  problem_description: string;
  corrective_action?: string | null;
  outcome_description?: string | null;
  priority: PriorityLevel;
  status: ActivityStatus;
  assigned_to?: string | null;
  assignee_name?: string | null;
  supervisor_id?: string | null;
  supervisor_name?: string | null;
  due_date?: string | null;
  submitted_at?: string | null;
  reviewed_at?: string | null;
  rejection_reason?: string | null;
  benefits_safety: boolean;
  benefits_space_sqft: number;
  benefits_time_seconds: number;
  benefits_cost_savings: number;
  benefits_summary?: string | null;
  asset_name?: string;
  location_name?: string;
  created_at: string;
  updated_at?: string;
  evidence: EvidenceMedia[];
  history: ActivityHistory[];
  comments: ActivityComment[];
}

export interface Zone {
  id: string;
  dept_id: string;
  name: string;
  code: string;
  description?: string;
  target_score: number;
  current_score: number;
  leader_name?: string;
  leader_id?: string;
  owner_name?: string;
  owner_id?: string;
  supervisor_name?: string;
}

export interface ZoneCreatePayload {
  plant_id?: string;
  dept_name?: string;
  dept_id?: string;
  name: string;
  code: string;
  description?: string;
  target_score?: number;
  current_score?: number;
  leader_id?: string;
  leader_name?: string;
}

export interface ZoneUpdatePayload {
  name?: string;
  code?: string;
  description?: string;
  target_score?: number;
  current_score?: number;
  dept_id?: string;
  leader_id?: string;
  leader_name?: string;
}

export interface Department {
  id: string;
  plant_id: string;
  name: string;
  code: string;
  zones: Zone[];
}

export interface Plant {
  id: string;
  org_id: string;
  name: string;
  code: string;
  location: string;
  is_active: boolean;
  departments: Department[];
}

export interface ZoneMetric {
  zone_id: string;
  zone_name: string;
  dept_name: string;
  score: number;
  active_tasks: number;
  overdue_tasks: number;
  status: "excellent" | "good" | "needs_attention";
}

export interface DashboardStats {
  plant_id: string;
  plant_name: string;
  total_activities: number;
  open_activities: number;
  in_progress_activities: number;
  submitted_activities: number;
  approved_activities: number;
  overdue_activities: number;
  monthly_audit_score: number;
  red_tag_count: number;
  avg_red_tag_age_days: number;
  zones: ZoneMetric[];
  category_counts: Record<string, number>;
  completion_trend: Array<{
    month: string;
    completion_rate: number;
    score: number;
  }>;
}

export interface RedTag {
  id: string;
  tag_number: string;
  plant_id: string;
  zone_id: string;
  logged_by_name?: string;
  item_name: string;
  item_category: string;
  quantity: number;
  reason: string;
  photo_url?: string;
  disposition: RedTagDisposition;
  disposition_notes?: string;
  is_closed: boolean;
  created_at: string;
  closed_at?: string;
  aging_days: number;
}

export interface AuditRun {
  photos?: string[];
  id: string;
  checklist_id?: string;
  plant_id: string;
  zone_id: string;
  zone_name?: string;
  auditor_name?: string;
  score_percentage: number;
  sort_score: number;
  set_in_order_score: number;
  shine_score: number;
  standardize_score: number;
  sustain_score: number;
  total_score: number;
  max_score: number;
  notes?: string;
  status: string;
  conducted_at: string;
}

export interface Profile {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: string;
  plant_id?: string;
  dept_id?: string;
  avatar_url?: string;
}
