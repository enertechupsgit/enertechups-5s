from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.models import AuditRun, Zone
from app.schemas.schemas import AuditRunCreate, AuditRunResponse

from app.core.access import Actor, get_actor, scope_query

router = APIRouter(prefix="/audits", tags=["5S Audits & Scoring"])

@router.get("", response_model=List[AuditRunResponse])
async def list_audits(plant_id: Optional[str] = None, zone_id: Optional[str] = None, actor: Actor = Depends(get_actor), db: AsyncSession = Depends(get_db)):
    query = scope_query(select(AuditRun).order_by(desc(AuditRun.conducted_at)), AuditRun, actor)
    if plant_id:
        query = query.where(AuditRun.plant_id == plant_id)
    if zone_id:
        query = query.where(AuditRun.zone_id == zone_id)
    
    result = await db.execute(query)
    audits = result.scalars().all()
    return audits

@router.post("", response_model=AuditRunResponse)
async def submit_audit(payload: AuditRunCreate, actor: Actor = Depends(get_actor), db: AsyncSession = Depends(get_db)):
    from app.models.models import Department
    zone = await db.get(Zone, payload.zone_id)
    department = await db.get(Department, zone.dept_id) if zone else None
    if not zone or not department or department.plant_id != payload.plant_id:
        raise HTTPException(422, "Select a zone belonging to this plant")
    # Calculate composite score percentage
    scores = [
        payload.sort_score,
        payload.set_in_order_score,
        payload.shine_score,
        payload.standardize_score,
        payload.sustain_score
    ]
    percentage = round(sum(scores) / len(scores), 1)

    audit = AuditRun(
        plant_id=payload.plant_id,
        zone_id=payload.zone_id,
        zone_name=zone.name,
        auditor_id=actor.profile.id,
        auditor_name=actor.name,
        score_percentage=percentage,
        sort_score=payload.sort_score,
        set_in_order_score=payload.set_in_order_score,
        shine_score=payload.shine_score,
        standardize_score=payload.standardize_score,
        sustain_score=payload.sustain_score,
        total_score=sum(scores),
        max_score=500.0,
        notes=payload.notes,
        status="completed",
        conducted_at=datetime.utcnow()
    )
    db.add(audit)

    # Update zone current score
    z_res = await db.execute(select(Zone).where(Zone.id == payload.zone_id))
    zone = z_res.scalar_one_or_none()
    if zone:
        zone.current_score = percentage

    await db.commit()
    await db.refresh(audit)
    return audit
