import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Float, DateTime, ForeignKey, Enum as SQLEnum, JSON
)
from sqlalchemy.orm import relationship
import enum
from app.core.database import Base

def generate_uuid() -> str:
    return str(uuid.uuid4())

# Enums
class UserRole(str, enum.Enum):
    SUPER_ADMIN = "super_admin"
    MANAGEMENT = "management"
    PLANT_MANAGER = "plant_manager"
    DEPT_HEAD = "dept_head"
    AUDITOR = "auditor"
    SUPERVISOR = "supervisor"
    ZONAL_LEADER = "zonal_leader"
    OPERATOR = "operator"

class FiveSCategory(str, enum.Enum):
    SORT = "sort_seiri"
    SET_IN_ORDER = "set_in_order_seiton"
    SHINE = "shine_seiso"
    STANDARDIZE = "standardize_seiketsu"
    SUSTAIN = "sustain_shitsuke"

class ActivityStatus(str, enum.Enum):
    DRAFT = "draft"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    SUBMITTED_FOR_REVIEW = "submitted_for_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"

class PriorityLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class MediaType(str, enum.Enum):
    BEFORE_PHOTO = "before_photo"
    AFTER_PHOTO = "after_photo"
    ACTION_STEP = "action_step"
    SUPPORTING_DOC = "supporting_doc"

class RedTagDisposition(str, enum.Enum):
    PENDING = "pending"
    RELOCATE = "relocate"
    SCRAP = "scrap"
    RETURN_TO_VENDOR = "return_to_vendor"
    HOLD_FOR_EVALUATION = "hold_for_evaluation"


# Core Plant Hierarchy
class Organization(Base):
    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    plants = relationship("Plant", back_populates="organization", cascade="all, delete-orphan")


class Plant(Base):
    __tablename__ = "plants"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    org_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False)
    location = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="plants")
    departments = relationship("Department", back_populates="plant", cascade="all, delete-orphan")
    activities = relationship("Activity", back_populates="plant")
    red_tags = relationship("RedTag", back_populates="plant")


class Department(Base):
    __tablename__ = "departments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    plant_id = Column(String(36), ForeignKey("plants.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    plant = relationship("Plant", back_populates="departments")
    zones = relationship("Zone", back_populates="department", cascade="all, delete-orphan")


class Zone(Base):
    __tablename__ = "zones"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    dept_id = Column(String(36), ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    code = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    target_score = Column(Float, default=90.0)
    current_score = Column(Float, default=85.0)
    leader_id = Column(String(36), nullable=True)
    leader_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    department = relationship("Department", back_populates="zones")
    activities = relationship("Activity", back_populates="zone")
    red_tags = relationship("RedTag", back_populates="zone")


# Users & Profiles
class Profile(Base):
    __tablename__ = "profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    role = Column(String(50), default=UserRole.ZONAL_LEADER.value, nullable=False)
    plant_id = Column(String(36), ForeignKey("plants.id"), nullable=True)
    dept_id = Column(String(36), ForeignKey("departments.id"), nullable=True)
    assigned_zone_id = Column(String(36), nullable=True)
    assigned_zone_name = Column(String(255), nullable=True)
    phone_number = Column(String(50), nullable=True)
    avatar_url = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    assigned_activities = relationship("Activity", foreign_keys="Activity.assigned_to", back_populates="assignee")
    supervised_activities = relationship("Activity", foreign_keys="Activity.supervisor_id", back_populates="supervisor")


# 5S Activity Engine
class WorkspaceSession(Base):
    __tablename__ = "workspace_sessions"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    profile_id = Column(String(36), ForeignKey("profiles.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class PasswordCredential(Base):
    __tablename__ = "password_credentials"
    profile_id = Column(String(36), ForeignKey("profiles.id"), primary_key=True)
    password_hash = Column(Text, nullable=False)
    failed_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AccessEvent(Base):
    __tablename__ = "access_events"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    profile_id = Column(String(36), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    detail = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Activity(Base):
    __tablename__ = "activities"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    activity_number = Column(String(50), unique=True, nullable=False)
    plant_id = Column(String(36), ForeignKey("plants.id"), nullable=False)
    zone_id = Column(String(36), ForeignKey("zones.id"), nullable=False)
    category = Column(String(50), nullable=False, default=FiveSCategory.SORT.value)
    title = Column(String(255), nullable=False)
    problem_description = Column(Text, nullable=False)
    corrective_action = Column(Text, nullable=True)
    outcome_description = Column(Text, nullable=True)
    priority = Column(String(50), default=PriorityLevel.MEDIUM.value)
    status = Column(String(50), default=ActivityStatus.DRAFT.value)
    
    assigned_to = Column(String(36), ForeignKey("profiles.id"), nullable=True)
    supervisor_id = Column(String(36), ForeignKey("profiles.id"), nullable=True)
    created_by = Column(String(36), ForeignKey("profiles.id"), nullable=True)
    
    due_date = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Measurable Benefits
    benefits_safety = Column(Boolean, default=False)
    benefits_space_sqft = Column(Float, default=0.0)
    benefits_time_seconds = Column(Float, default=0.0)
    benefits_cost_savings = Column(Float, default=0.0)
    benefits_summary = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    plant = relationship("Plant", back_populates="activities")
    zone = relationship("Zone", back_populates="activities")
    assignee = relationship("Profile", foreign_keys=[assigned_to], back_populates="assigned_activities")
    supervisor = relationship("Profile", foreign_keys=[supervisor_id], back_populates="supervised_activities")
    evidence = relationship("EvidenceMedia", back_populates="activity", cascade="all, delete-orphan")
    history = relationship("ActivityHistory", back_populates="activity", cascade="all, delete-orphan")
    comments = relationship("ActivityComment", back_populates="activity", cascade="all, delete-orphan")


class EvidenceMedia(Base):
    __tablename__ = "evidence_media"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    activity_id = Column(String(36), ForeignKey("activities.id", ondelete="CASCADE"), nullable=False)
    media_type = Column(String(50), nullable=False)  # before_photo, after_photo, etc.
    file_name = Column(String(255), nullable=False)
    file_url = Column(Text, nullable=False)
    storage_path = Column(Text, nullable=True)
    file_size_bytes = Column(Integer, default=0)
    mime_type = Column(String(100), default="image/jpeg")
    annotations_json = Column(JSON, nullable=True)
    uploaded_by = Column(String(36), ForeignKey("profiles.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    activity = relationship("Activity", back_populates="evidence")


class ActivityHistory(Base):
    __tablename__ = "activity_history"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    activity_id = Column(String(36), ForeignKey("activities.id", ondelete="CASCADE"), nullable=False)
    actor_id = Column(String(36), ForeignKey("profiles.id"), nullable=True)
    actor_name = Column(String(255), nullable=True)
    from_status = Column(String(50), nullable=True)
    to_status = Column(String(50), nullable=False)
    action_note = Column(Text, nullable=True)
    changed_fields = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    activity = relationship("Activity", back_populates="history")


class ActivityComment(Base):
    __tablename__ = "activity_comments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    activity_id = Column(String(36), ForeignKey("activities.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(String(36), ForeignKey("profiles.id"), nullable=True)
    author_name = Column(String(255), nullable=False)
    comment = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    activity = relationship("Activity", back_populates="comments")


# Red Tagging Module
class RedTag(Base):
    __tablename__ = "red_tags"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tag_number = Column(String(50), unique=True, nullable=False)
    plant_id = Column(String(36), ForeignKey("plants.id"), nullable=False)
    zone_id = Column(String(36), ForeignKey("zones.id"), nullable=False)
    logged_by = Column(String(36), ForeignKey("profiles.id"), nullable=True)
    logged_by_name = Column(String(255), nullable=True)
    
    item_name = Column(String(255), nullable=False)
    item_category = Column(String(100), default="Equipment/Tool")
    quantity = Column(Integer, default=1)
    reason = Column(Text, nullable=False)
    photo_url = Column(Text, nullable=True)
    
    disposition = Column(String(50), default=RedTagDisposition.PENDING.value)
    disposition_notes = Column(Text, nullable=True)
    disposition_by = Column(String(36), ForeignKey("profiles.id"), nullable=True)
    disposition_date = Column(DateTime, nullable=True)
    
    is_closed = Column(Boolean, default=False)
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    plant = relationship("Plant", back_populates="red_tags")
    zone = relationship("Zone", back_populates="red_tags")


# 5S Audits & Scoring
class AuditChecklist(Base):
    __tablename__ = "audit_checklists"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    plant_id = Column(String(36), ForeignKey("plants.id"), nullable=False)
    title = Column(String(255), nullable=False)
    version = Column(Integer, default=1)
    items = Column(JSON, nullable=False)  # [{ id, category, question, max_score, weight }]
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Asset(Base):
    __tablename__ = "assets"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    plant_id = Column(String(36), ForeignKey("plants.id"), nullable=False, index=True)
    zone_id = Column(String(36), ForeignKey("zones.id"), nullable=True)
    parent_id = Column(String(36), ForeignKey("assets.id"), nullable=True)
    name = Column(String(255), nullable=False)
    code = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="online")
    manufacturer = Column(String(255), nullable=True)
    model = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AssetStatusEvent(Base):
    __tablename__ = "asset_status_events"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    asset_id = Column(String(36), ForeignKey("assets.id"), nullable=False, index=True)
    status = Column(String(50), nullable=False)
    note = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditRun(Base):
    __tablename__ = "audit_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    checklist_id = Column(String(36), ForeignKey("audit_checklists.id"), nullable=True)
    plant_id = Column(String(36), ForeignKey("plants.id"), nullable=False)
    zone_id = Column(String(36), ForeignKey("zones.id"), nullable=False)
    zone_name = Column(String(255), nullable=True)
    auditor_id = Column(String(36), ForeignKey("profiles.id"), nullable=True)
    auditor_name = Column(String(255), nullable=True)
    
    score_percentage = Column(Float, nullable=False)
    sort_score = Column(Float, default=90.0)
    set_in_order_score = Column(Float, default=85.0)
    shine_score = Column(Float, default=95.0)
    standardize_score = Column(Float, default=88.0)
    sustain_score = Column(Float, default=82.0)
    
    total_score = Column(Float, nullable=False)
    max_score = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)
    status = Column(String(50), default="completed")
    conducted_at = Column(DateTime, default=datetime.utcnow)
