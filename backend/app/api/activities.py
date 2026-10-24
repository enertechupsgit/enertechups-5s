from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from datetime import datetime
import uuid
from app.core.images import evidence_values

from app.core.database import get_db
from app.models.models import (
    Activity, EvidenceMedia, ActivityHistory, ActivityComment, Profile, Zone, Department,
    ActivityStatus, MediaType, CommentPhoto
)
from app.schemas.schemas import (
    ActivityCreate, ActivityUpdate, ActivityResponse, ActivitySubmitReview,
    ActivityReviewDecision, EvidenceMediaCreate, EvidenceMediaResponse,
    ActivityCommentCreate, ActivityCommentResponse, ReportSubmissionRequest
)

from app.core.access import Actor, get_actor, scope_query

router = APIRouter(prefix="/activities", tags=["5S Activities"])

async def locked_activity(db, activity_id):
    # Refresh the identity map after waiting for a competing PostgreSQL transition.
    return (await db.execute(select(Activity).where(Activity.id == activity_id).with_for_update().execution_options(populate_existing=True))).scalar_one_or_none()

@router.post("/{activity_id}/start", response_model=ActivityResponse)
async def start_activity(activity_id: str, actor: Actor = Depends(get_actor), db: AsyncSession = Depends(get_db)):
    activity = await locked_activity(db, activity_id)
    if not activity:
        raise HTTPException(404, "Activity not found")
    if activity.status not in ["draft", "assigned", "rejected"]:
        raise HTTPException(409, "Only open or changes-requested work can be started")
    previous = activity.status
    activity.status = "in_progress"
    db.add(ActivityHistory(activity_id=activity_id, actor_id=actor.profile.id, actor_name=actor.name, from_status=previous, to_status="in_progress", action_note="Work started"))
    await db.commit()
    return await build_activity_response(activity, db, actor)

@router.post("/{activity_id}/report", response_model=ActivityResponse)
async def submit_report(activity_id: str, payload: ReportSubmissionRequest, actor: Actor = Depends(get_actor), db: AsyncSession = Depends(get_db)):
    activity = await locked_activity(db, activity_id)
    if not activity:
        raise HTTPException(404, "Activity not found")
    if activity.status not in ["draft", "assigned", "in_progress", "rejected"]:
        raise HTTPException(409, "This activity is not open for submission")
    if not payload.corrective_action.strip() or not payload.after_photo_url.strip():
        raise HTTPException(422, "Corrective action and after-photo evidence are required")
    previous = activity.status
    activity.corrective_action = payload.corrective_action.strip()
    activity.outcome_description = payload.outcome_description
    for field in ["benefits_safety", "benefits_space_sqft", "benefits_time_seconds", "benefits_cost_savings", "benefits_summary"]:
        setattr(activity, field, getattr(payload, field))
    activity.status = "submitted_for_review"
    activity.submitted_at = datetime.utcnow()
    activity.rejection_reason = None
    if payload.before_photo_url:
        db.add(EvidenceMedia(activity_id=activity_id, media_type="before_photo", uploaded_by=actor.profile.id, **evidence_values(payload.before_photo_url, "before-evidence")))
    db.add(EvidenceMedia(activity_id=activity_id, media_type="after_photo", uploaded_by=actor.profile.id, **evidence_values(payload.after_photo_url, "after-evidence")))
    db.add(ActivityHistory(activity_id=activity_id, actor_id=actor.profile.id, actor_name=actor.name, from_status=previous, to_status="submitted_for_review", action_note="Corrective action submitted with after evidence"))
    await db.commit()
    return await build_activity_response(activity, db, actor)

async def build_activity_response(act: Activity, db: AsyncSession, actor: Actor) -> dict:
    # Fetch evidence
    ev_res = await db.execute(select(EvidenceMedia).where(EvidenceMedia.activity_id == act.id).order_by(EvidenceMedia.created_at.asc()))
    evidence_list = ev_res.scalars().all()

    # Fetch history
    hist_res = await db.execute(select(ActivityHistory).where(ActivityHistory.activity_id == act.id).order_by(ActivityHistory.created_at.desc()))
    history_list = hist_res.scalars().all()

    # Fetch comments
    comm_res = await db.execute(select(ActivityComment).where(ActivityComment.activity_id == act.id).order_by(ActivityComment.created_at.asc()))
    comments_list = comm_res.scalars().all()
    if "work.review" not in actor.permissions:
        comments_list = [c for c in comments_list if not c.is_internal]
    photos = (await db.execute(select(CommentPhoto).where(CommentPhoto.comment_id.in_([c.id for c in comments_list])))).scalars().all() if comments_list else []
    comments_list = [{**ActivityCommentResponse.model_validate(c).model_dump(), "attachments": [photo.file_url for photo in photos if photo.comment_id == c.id]} for c in comments_list]

    # Assignee name
    assignee_name = None
    if act.assigned_to:
        p_res = await db.execute(select(Profile).where(Profile.id == act.assigned_to))
        p = p_res.scalar_one_or_none()
        if p:
            assignee_name = f"{p.first_name} {p.last_name}"

    # Supervisor name
    supervisor_name = None
    if act.supervisor_id:
        s_res = await db.execute(select(Profile).where(Profile.id == act.supervisor_id))
        s = s_res.scalar_one_or_none()
        if s:
            supervisor_name = f"{s.first_name} {s.last_name}"

    return {
        "id": act.id,
        "activity_number": act.activity_number,
        "plant_id": act.plant_id,
        "zone_id": act.zone_id,
        "category": act.category,
        "title": act.title,
        "problem_description": act.problem_description,
        "corrective_action": act.corrective_action,
        "outcome_description": act.outcome_description,
        "priority": act.priority,
        "status": act.status,
        "assigned_to": act.assigned_to,
        "assignee_name": assignee_name,
        "supervisor_id": act.supervisor_id,
        "supervisor_name": supervisor_name,
        "due_date": act.due_date,
        "submitted_at": act.submitted_at,
        "reviewed_at": act.reviewed_at,
        "rejection_reason": act.rejection_reason,
        "benefits_safety": act.benefits_safety,
        "benefits_space_sqft": act.benefits_space_sqft,
        "benefits_time_seconds": act.benefits_time_seconds,
        "benefits_cost_savings": act.benefits_cost_savings,
        "benefits_summary": act.benefits_summary,
        "created_at": act.created_at,
        "updated_at": act.updated_at,
        "evidence": evidence_list,
        "history": history_list,
        "comments": comments_list,
    }


@router.get("", response_model=List[ActivityResponse])
async def list_activities(
    plant_id: Optional[str] = None,
    zone_id: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[str] = None,
    actor: Actor = Depends(get_actor), db: AsyncSession = Depends(get_db)
):
    query = scope_query(select(Activity).order_by(desc(Activity.created_at)), Activity, actor)
    if plant_id:
        query = query.where(Activity.plant_id == plant_id)
    if zone_id:
        query = query.where(Activity.zone_id == zone_id)
    if status:
        query = query.where(Activity.status == status)
    if category:
        query = query.where(Activity.category == category)
    if priority:
        query = query.where(Activity.priority == priority)
    if assigned_to:
        query = query.where(Activity.assigned_to == assigned_to)

    result = await db.execute(query)
    activities = result.scalars().all()

    responses = []
    for act in activities:
        responses.append(await build_activity_response(act, db, actor))
    return responses


@router.post("", response_model=ActivityResponse)
async def create_activity(payload: ActivityCreate, actor: Actor = Depends(get_actor), db: AsyncSession = Depends(get_db)):
    # Generate sequential or unique activity number
    year = datetime.utcnow().year
    rand_seq = uuid.uuid4().hex[:12].upper()
    activity_num = f"5S-{year}-{rand_seq}"

    initial_status = ActivityStatus.ASSIGNED.value if payload.assigned_to else ActivityStatus.DRAFT.value

    target_zone_id = payload.zone_id

    new_activity = Activity(
        activity_number=activity_num,
        plant_id=payload.plant_id,
        zone_id=target_zone_id,
        category=payload.category,
        title=payload.title,
        problem_description=payload.problem_description,
        corrective_action=payload.corrective_action,
        outcome_description=payload.outcome_description,
        priority=payload.priority,
        status=initial_status,
        assigned_to=payload.assigned_to,
        created_by=actor.profile.id,
        supervisor_id=payload.supervisor_id,
        due_date=payload.due_date,
        benefits_safety=payload.benefits_safety,
        benefits_space_sqft=payload.benefits_space_sqft,
        benefits_time_seconds=payload.benefits_time_seconds,
        benefits_cost_savings=payload.benefits_cost_savings,
        benefits_summary=payload.benefits_summary,
    )
    db.add(new_activity)
    await db.flush()

    # Record history
    history_entry = ActivityHistory(
        activity_id=new_activity.id,
        actor_id=actor.profile.id, actor_name=actor.name,
        from_status=None,
        to_status=initial_status,
        action_note="5S Activity created and registered."
    )
    db.add(history_entry)

    # If initial before photo provided
    if payload.initial_before_photo_url:
        evidence = EvidenceMedia(
            activity_id=new_activity.id,
            media_type=MediaType.BEFORE_PHOTO.value,
            uploaded_by=actor.profile.id,
            **evidence_values(payload.initial_before_photo_url, "before-evidence")
        )
        db.add(evidence)

    await db.commit()
    await db.refresh(new_activity)
    return await build_activity_response(new_activity, db, actor)


@router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity(activity_id: str, actor: Actor = Depends(get_actor), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Activity).where(Activity.id == activity_id))
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")
    return await build_activity_response(activity, db, actor)


@router.put("/{activity_id}", response_model=ActivityResponse)
async def update_activity(activity_id: str, payload: ActivityUpdate, actor: Actor = Depends(get_actor), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Activity).where(Activity.id == activity_id))
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    update_data = payload.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(activity, field, value)

    activity.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(activity)
    return await build_activity_response(activity, db, actor)


@router.post("/{activity_id}/evidence", response_model=EvidenceMediaResponse)
async def upload_evidence(activity_id: str, payload: EvidenceMediaCreate, actor: Actor = Depends(get_actor), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Activity).where(Activity.id == activity_id))
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    if activity.status in {"submitted_for_review", "completed", "approved"}:
        raise HTTPException(409, "Evidence is locked while under review or after completion")
    evidence = EvidenceMedia(activity_id=activity_id, media_type=payload.media_type, uploaded_by=actor.profile.id, annotations_json=payload.annotations_json, **evidence_values(payload.file_url, "evidence"))
    db.add(evidence)

    # Auto advance to in_progress if currently assigned
    if activity.status == ActivityStatus.ASSIGNED.value:
        activity.status = ActivityStatus.IN_PROGRESS.value
        db.add(ActivityHistory(
            activity_id=activity.id,
            actor_id=actor.profile.id, actor_name=actor.name,
            from_status=ActivityStatus.ASSIGNED.value,
            to_status=ActivityStatus.IN_PROGRESS.value,
            action_note="Evidence uploaded; status moved to In Progress."
        ))

    await db.commit()
    await db.refresh(evidence)
    return evidence


@router.post("/{activity_id}/submit", response_model=ActivityResponse)
async def submit_for_review(activity_id: str, payload: ActivitySubmitReview, actor: Actor = Depends(get_actor), db: AsyncSession = Depends(get_db)):
    raise HTTPException(409, "Use report submission with corrective action and after evidence")


@router.post("/{activity_id}/review", response_model=ActivityResponse)
async def review_activity(activity_id: str, payload: ActivityReviewDecision, actor: Actor = Depends(get_actor), db: AsyncSession = Depends(get_db)):
    activity = await locked_activity(db, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    if activity.status != ActivityStatus.SUBMITTED_FOR_REVIEW.value:
        raise HTTPException(409, "Only submitted activities can be reviewed")

    old_status = activity.status
    activity.reviewed_at = datetime.utcnow()

    if payload.decision == "approve":
        activity.status = ActivityStatus.APPROVED.value
        note = payload.review_notes or "Activity verified and approved."
        activity.rejection_reason = None
        
        # Add history
        db.add(ActivityHistory(
            activity_id=activity.id,
            actor_id=actor.profile.id, actor_name=actor.name,
            from_status=old_status,
            to_status=ActivityStatus.APPROVED.value,
            action_note=f"Approved: {note}"
        ))
        
        # Complete
        activity.status = ActivityStatus.COMPLETED.value
        db.add(ActivityHistory(
            activity_id=activity.id,
            actor_name="System",
            from_status=ActivityStatus.APPROVED.value,
            to_status=ActivityStatus.COMPLETED.value,
            action_note="5S Activity officially completed and closed."
        ))

    elif payload.decision == "reject":
        if not payload.rejection_reason:
            raise HTTPException(status_code=400, detail="Rejection reason is mandatory when rejecting an activity.")
        
        activity.status = ActivityStatus.REJECTED.value
        activity.rejection_reason = payload.rejection_reason
        
        db.add(ActivityHistory(
            activity_id=activity.id,
            actor_id=actor.profile.id, actor_name=actor.name,
            from_status=old_status,
            to_status=ActivityStatus.REJECTED.value,
            action_note=f"Rejected: {payload.rejection_reason}"
        ))

    else:
        raise HTTPException(status_code=400, detail="Invalid decision. Must be 'approve' or 'reject'.")

    await db.commit()
    await db.refresh(activity)
    return await build_activity_response(activity, db, actor)


@router.post("/{activity_id}/comments", response_model=ActivityCommentResponse)
async def add_comment(activity_id: str, payload: ActivityCommentCreate, actor: Actor = Depends(get_actor), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Activity).where(Activity.id == activity_id))
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    if payload.is_internal and "work.review" not in actor.permissions:
        raise HTTPException(403, "Only reviewers can post internal comments")
    comment = ActivityComment(
        activity_id=activity_id,
        author_id=actor.profile.id, author_name=actor.name,
        comment=payload.comment,
        is_internal=payload.is_internal
    )
    db.add(comment)
    await db.flush()
    for photo in payload.attachments:
        db.add(CommentPhoto(comment_id=comment.id, file_url=photo))
    db.add(ActivityHistory(activity_id=activity_id, actor_id=actor.profile.id, actor_name=actor.name, to_status=activity.status, action_note="Comment added"))
    await db.commit()
    await db.refresh(comment)
    return {**ActivityCommentResponse.model_validate(comment).model_dump(), "attachments": payload.attachments}
