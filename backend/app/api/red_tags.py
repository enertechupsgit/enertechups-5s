from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from datetime import datetime
import uuid

from app.core.database import get_db
from app.models.models import RedTag
from app.schemas.schemas import RedTagCreate, RedTagDispositionUpdate, RedTagResponse

from app.core.access import Actor, get_actor, scope_query

router = APIRouter(prefix="/redtags", tags=["Red-Tag Management"])

def build_red_tag_dict(rt: RedTag) -> dict:
    now = datetime.utcnow()
    ref_date = rt.closed_at if rt.is_closed and rt.closed_at else now
    age = (ref_date - rt.created_at).days
    return {
        "id": rt.id,
        "tag_number": rt.tag_number,
        "plant_id": rt.plant_id,
        "zone_id": rt.zone_id,
        "logged_by_name": rt.logged_by_name,
        "item_name": rt.item_name,
        "item_category": rt.item_category,
        "quantity": rt.quantity,
        "reason": rt.reason,
        "photo_url": rt.photo_url,
        "disposition": rt.disposition,
        "disposition_notes": rt.disposition_notes,
        "is_closed": rt.is_closed,
        "created_at": rt.created_at,
        "closed_at": rt.closed_at,
        "aging_days": max(age, 0)
    }

@router.get("", response_model=List[RedTagResponse])
async def list_red_tags(
    plant_id: Optional[str] = None,
    zone_id: Optional[str] = None,
    is_closed: Optional[bool] = None,
    actor: Actor = Depends(get_actor), db: AsyncSession = Depends(get_db)
):
    query = scope_query(select(RedTag).order_by(desc(RedTag.created_at)), RedTag, actor)
    if plant_id:
        query = query.where(RedTag.plant_id == plant_id)
    if zone_id:
        query = query.where(RedTag.zone_id == zone_id)
    if is_closed is not None:
        query = query.where(RedTag.is_closed == is_closed)

    result = await db.execute(query)
    tags = result.scalars().all()
    return [build_red_tag_dict(t) for t in tags]

@router.post("", response_model=RedTagResponse)
async def create_red_tag(payload: RedTagCreate, actor: Actor = Depends(get_actor), db: AsyncSession = Depends(get_db)):
    year = datetime.utcnow().year
    rand_seq = uuid.uuid4().hex[:12].upper()
    tag_num = f"RT-{year}-{rand_seq}"

    rt = RedTag(
        tag_number=tag_num,
        plant_id=payload.plant_id,
        zone_id=payload.zone_id,
        logged_by=actor.profile.id,
        logged_by_name=actor.name,
        item_name=payload.item_name,
        item_category=payload.item_category,
        quantity=payload.quantity,
        reason=payload.reason,
        photo_url=payload.photo_url,
        disposition="pending",
        is_closed=False
    )
    db.add(rt)
    await db.commit()
    await db.refresh(rt)
    return build_red_tag_dict(rt)

@router.put("/{tag_id}/disposition", response_model=RedTagResponse)
async def update_disposition(tag_id: str, payload: RedTagDispositionUpdate, actor: Actor = Depends(get_actor), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RedTag).where(RedTag.id == tag_id))
    rt = result.scalar_one_or_none()
    if not rt:
        raise HTTPException(status_code=404, detail="Red-Tag item not found")

    if rt.is_closed:
        raise HTTPException(409, "This red tag is already closed")

    rt.disposition_by = actor.profile.id
    rt.disposition = payload.disposition
    rt.disposition_notes = payload.disposition_notes
    rt.disposition_date = datetime.utcnow()
    rt.is_closed = payload.is_closed
    if payload.is_closed:
        rt.closed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(rt)
    return build_red_tag_dict(rt)
