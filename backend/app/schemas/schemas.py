from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.models import FiveSCategory, ActivityStatus, PriorityLevel, MediaType, RedTagDisposition, UserRole

# Plant Hierarchy Schemas
class ZoneBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    target_score: float = 90.0

class ZoneCreate(ZoneBase):
    plant_id: Optional[str] = None
    dept_id: Optional[str] = None
    dept_name: Optional[str] = None
    current_score: Optional[float] = 85.0
    leader_id: Optional[str] = None
    leader_name: Optional[str] = None

class ZoneUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    target_score: Optional[float] = None
    current_score: Optional[float] = None
    dept_id: Optional[str] = None
    leader_id: Optional[str] = None
    leader_name: Optional[str] = None

class ZoneResponse(ZoneBase):
    id: str
    dept_id: str
    current_score: float = 85.0
    leader_id: Optional[str] = None
    leader_name: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

class DepartmentCreate(BaseModel):
    plant_id: str
    name: str
    code: str

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None

class DepartmentResponse(BaseModel):
    id: str
    plant_id: str
    name: str
    code: str
    zones: List[ZoneResponse] = []
    class Config:
        from_attributes = True

class PlantResponse(BaseModel):
    id: str
    org_id: str
    name: str
    code: str
    location: Optional[str] = None
    is_active: bool
    departments: List[DepartmentResponse] = []
    class Config:
        from_attributes = True


# User / Profile Schemas
class ProfileBase(BaseModel):
    email: str
    first_name: str
    last_name: str
    role: str = UserRole.ZONAL_LEADER.value
    plant_id: Optional[str] = None
    dept_id: Optional[str] = None
    assigned_zone_id: Optional[str] = None
    assigned_zone_name: Optional[str] = None
    phone_number: Optional[str] = None
    avatar_url: Optional[str] = None

class ProfileResponse(ProfileBase):
    id: str
    is_active: bool
    created_at: datetime
    class Config:
        from_attributes = True

# Zonal Leader Management Schemas
class ZonalLeaderCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone_number: Optional[str] = None
    plant_id: str
    dept_id: Optional[str] = None
    assigned_zone_id: Optional[str] = None
    role: Optional[str] = "zonal_leader"

class ZonalLeaderUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    assigned_zone_id: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class ZonalLeaderResponse(BaseModel):
    id: str
    first_name: str
    last_name: str
    email: str
    phone_number: Optional[str] = None
    role: str
    plant_id: Optional[str] = None
    dept_id: Optional[str] = None
    assigned_zone_id: Optional[str] = None
    assigned_zone_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    active_tasks_count: int = 0
    completed_tasks_count: int = 0
    created_at: datetime
    class Config:
        from_attributes = True

class ReportSubmissionRequest(BaseModel):
    corrective_action: str
    outcome_description: Optional[str] = None
    before_photo_url: Optional[str] = None
    after_photo_url: str
    benefits_safety: bool = False
    benefits_space_sqft: float = 0.0
    benefits_time_seconds: float = 0.0
    benefits_cost_savings: float = 0.0
    benefits_summary: Optional[str] = None

class ReportReviewRequest(BaseModel):
    action: str  # "approve" or "request_changes"
    feedback_note: Optional[str] = None
    reviewed_by: Optional[str] = None


# Evidence Media Schemas
class EvidenceMediaCreate(BaseModel):
    media_type: str = MediaType.BEFORE_PHOTO.value
    file_name: str
    file_url: str
    file_size_bytes: int = 0
    mime_type: str = "image/jpeg"
    annotations_json: Optional[Dict[str, Any]] = None

class EvidenceMediaResponse(EvidenceMediaCreate):
    id: str
    activity_id: str
    uploaded_by: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True


# Activity History & Comments
class ActivityHistoryResponse(BaseModel):
    id: str
    activity_id: str
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    from_status: Optional[str] = None
    to_status: str
    action_note: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True

class ActivityCommentCreate(BaseModel):
    author_name: str
    comment: str
    is_internal: bool = False

class ActivityCommentResponse(ActivityCommentCreate):
    id: str
    activity_id: str
    author_id: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True


# 5S Activity Schemas
class ActivityCreate(BaseModel):
    plant_id: str
    zone_id: str
    category: str = FiveSCategory.SORT.value
    title: str
    problem_description: str
    corrective_action: Optional[str] = None
    outcome_description: Optional[str] = None
    priority: str = PriorityLevel.MEDIUM.value
    assigned_to: Optional[str] = None
    supervisor_id: Optional[str] = None
    due_date: Optional[datetime] = None
    
    # Benefits
    benefits_safety: bool = False
    benefits_space_sqft: float = 0.0
    benefits_time_seconds: float = 0.0
    benefits_cost_savings: float = 0.0
    benefits_summary: Optional[str] = None

    # Optional initial before photo
    initial_before_photo_url: Optional[str] = None

class ActivityUpdate(BaseModel):
    title: Optional[str] = None
    problem_description: Optional[str] = None
    corrective_action: Optional[str] = None
    outcome_description: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    supervisor_id: Optional[str] = None
    due_date: Optional[datetime] = None
    benefits_safety: Optional[bool] = None
    benefits_space_sqft: Optional[float] = None
    benefits_time_seconds: Optional[float] = None
    benefits_cost_savings: Optional[float] = None
    benefits_summary: Optional[str] = None

class ActivitySubmitReview(BaseModel):
    actor_name: str = "Floor Operator"
    submission_note: Optional[str] = None
    outcome_description: Optional[str] = None
    benefits_safety: Optional[bool] = None
    benefits_space_sqft: Optional[float] = None
    benefits_time_seconds: Optional[float] = None
    benefits_cost_savings: Optional[float] = None
    benefits_summary: Optional[str] = None

class ActivityReviewDecision(BaseModel):
    decision: str = Field(..., description="'approve' or 'reject'")
    reviewer_name: str = "Area Supervisor"
    rejection_reason: Optional[str] = Field(None, description="Mandatory when decision is 'reject'")
    review_notes: Optional[str] = None

class ActivityResponse(BaseModel):
    id: str
    activity_number: str
    plant_id: str
    zone_id: str
    category: str
    title: str
    problem_description: str
    corrective_action: Optional[str] = None
    outcome_description: Optional[str] = None
    priority: str
    status: str
    
    assigned_to: Optional[str] = None
    assignee_name: Optional[str] = None
    supervisor_id: Optional[str] = None
    supervisor_name: Optional[str] = None
    
    due_date: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    
    benefits_safety: bool
    benefits_space_sqft: float
    benefits_time_seconds: float
    benefits_cost_savings: float
    benefits_summary: Optional[str] = None
    
    created_at: datetime
    updated_at: datetime
    
    evidence: List[EvidenceMediaResponse] = []
    history: List[ActivityHistoryResponse] = []
    comments: List[ActivityCommentResponse] = []

    class Config:
        from_attributes = True


# Red Tags
class RedTagCreate(BaseModel):
    plant_id: str
    zone_id: str
    item_name: str
    item_category: str = "Tool/Fixture"
    quantity: int = 1
    reason: str
    photo_url: Optional[str] = None
    logged_by_name: Optional[str] = "Floor Operator"

class RedTagDispositionUpdate(BaseModel):
    disposition: str = RedTagDisposition.RELOCATE.value
    disposition_notes: str
    disposition_by_name: str = "5S Coordinator"
    is_closed: bool = True

class RedTagResponse(BaseModel):
    id: str
    tag_number: str
    plant_id: str
    zone_id: str
    logged_by_name: Optional[str] = None
    item_name: str
    item_category: str
    quantity: int
    reason: str
    photo_url: Optional[str] = None
    disposition: str
    disposition_notes: Optional[str] = None
    is_closed: bool
    created_at: datetime
    closed_at: Optional[datetime] = None
    aging_days: int = 0

    class Config:
        from_attributes = True


# Audit Runs
class AuditRunCreate(BaseModel):
    plant_id: str
    zone_id: str
    zone_name: str
    auditor_name: str = "Lead Auditor"
    sort_score: float = Field(ge=0, le=100)
    set_in_order_score: float = Field(ge=0, le=100)
    shine_score: float = Field(ge=0, le=100)
    standardize_score: float = Field(ge=0, le=100)
    sustain_score: float = Field(ge=0, le=100)
    notes: Optional[str] = None

class AuditRunResponse(BaseModel):
    id: str
    plant_id: str
    zone_id: str
    zone_name: Optional[str] = None
    auditor_name: Optional[str] = None
    score_percentage: float
    sort_score: float
    set_in_order_score: float
    shine_score: float
    standardize_score: float
    sustain_score: float
    notes: Optional[str] = None
    status: str
    conducted_at: datetime

    class Config:
        from_attributes = True


# Command Center Dashboard Stats
class ZoneMetric(BaseModel):
    zone_id: str
    zone_name: str
    dept_name: str
    score: float
    active_tasks: int
    overdue_tasks: int
    status: str  # excellent, good, needs_attention, critical

class DashboardStatsResponse(BaseModel):
    plant_id: str
    plant_name: str
    total_activities: int
    open_activities: int
    in_progress_activities: int
    submitted_activities: int
    approved_activities: int
    overdue_activities: int
    monthly_audit_score: float
    red_tag_count: int
    avg_red_tag_age_days: float
    zones: List[ZoneMetric] = []
    category_counts: Dict[str, int] = {}
    completion_trend: List[Dict[str, Any]] = []
