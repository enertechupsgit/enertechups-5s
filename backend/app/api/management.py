from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.models.models import Profile, Zone, Activity, RedTag, AuditRun, ActivityStatus, UserRole
from app.schemas.schemas import (
    ZonalLeaderCreate,
    ZonalLeaderUpdate,
    ZonalLeaderResponse
)

from app.core.access import Actor, get_actor, scope_query

router = APIRouter(prefix="/management", tags=["Management Administration"])


@router.get("/zonal-leaders", response_model=List[ZonalLeaderResponse])
async def list_zonal_leaders(plant_id: Optional[str] = None, actor: Actor = Depends(get_actor), db: AsyncSession = Depends(get_db)):
    """List all active Zonal Leaders with their assigned zone and live task statistics."""
    query = select(Profile).where(Profile.plant_id.in_(actor.plant_ids),
        Profile.is_active == True,
        Profile.role.in_([UserRole.ZONAL_LEADER.value, UserRole.OPERATOR.value, UserRole.SUPERVISOR.value, UserRole.AUDITOR.value, UserRole.MANAGEMENT.value, "director", "hr", "admin"])
    )
    if plant_id:
        query = query.where(Profile.plant_id == plant_id)
    
    result = await db.execute(query)
    profiles = result.scalars().all()
    
    response_list = []
    for p in profiles:
        # Get zone name if assigned
        zone_name = None
        if p.assigned_zone_id:
            z_res = await db.execute(select(Zone).where(Zone.id == p.assigned_zone_id))
            z = z_res.scalar_one_or_none()
            if z:
                zone_name = z.name
        
        # Count active tasks assigned to this leader
        active_cnt_res = await db.execute(
            select(func.count(Activity.id)).where(
                and_(
                    Activity.assigned_to == p.id,
                    Activity.status.in_([
                        ActivityStatus.ASSIGNED.value,
                        ActivityStatus.IN_PROGRESS.value,
                        ActivityStatus.SUBMITTED_FOR_REVIEW.value
                    ])
                )
            )
        )
        active_tasks = active_cnt_res.scalar() or 0
        
        # Count completed tasks
        comp_cnt_res = await db.execute(
            select(func.count(Activity.id)).where(
                and_(
                    Activity.assigned_to == p.id,
                    Activity.status.in_([
                        ActivityStatus.APPROVED.value,
                        ActivityStatus.COMPLETED.value
                    ])
                )
            )
        )
        completed_tasks = comp_cnt_res.scalar() or 0
        
        response_list.append({
            "id": p.id,
            "first_name": p.first_name,
            "last_name": p.last_name,
            "email": p.email,
            "phone_number": p.phone_number,
            "role": p.role,
            "plant_id": p.plant_id,
            "dept_id": p.dept_id,
            "assigned_zone_id": p.assigned_zone_id,
            "assigned_zone_name": zone_name or p.assigned_zone_name,
            "avatar_url": p.avatar_url or f"https://api.dicebear.com/7.x/initials/svg?seed={p.first_name}+{p.last_name}",
            "is_active": p.is_active,
            "active_tasks_count": active_tasks,
            "completed_tasks_count": completed_tasks,
            "created_at": p.created_at
        })
        
    return response_list


@router.post("/zonal-leaders", response_model=ZonalLeaderResponse)
async def create_zonal_leader(payload: ZonalLeaderCreate, actor: Actor = Depends(get_actor), db: AsyncSession = Depends(get_db)):
    """Management adds a new Zonal Leader and optionally links them to a Zone."""
    if payload.role not in [None, "zonal_leader", "operator", "supervisor", "auditor"]:
        raise HTTPException(403, "This role cannot be granted through people management")
    # Check if email exists
    existing = await db.execute(select(Profile).where(Profile.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="A user with this email already exists.")
    
    zone = None
    assigned_dept_id = payload.dept_id
    assigned_zone_name = None

    if payload.assigned_zone_id and payload.assigned_zone_id.strip() and payload.assigned_zone_id != "unassigned":
        z_res = await db.execute(select(Zone).where(Zone.id == payload.assigned_zone_id))
        zone = z_res.scalar_one_or_none()
        if zone:
            assigned_dept_id = zone.dept_id
            assigned_zone_name = zone.name

    new_profile = Profile(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone_number=payload.phone_number,
        plant_id=payload.plant_id,
        dept_id=assigned_dept_id,
        assigned_zone_id=zone.id if zone else None,
        assigned_zone_name=assigned_zone_name,
        role=payload.role or UserRole.ZONAL_LEADER.value,
        avatar_url=f"https://api.dicebear.com/7.x/initials/svg?seed={payload.first_name}+{payload.last_name}",
        is_active=True
    )
    db.add(new_profile)
    await db.flush()
    
    # Update zone with leader info if zone was selected
    if zone:
        zone.leader_id = new_profile.id
        zone.leader_name = f"{new_profile.first_name} {new_profile.last_name}"
    
    await db.commit()
    await db.refresh(new_profile)
    
    return {
        "id": new_profile.id,
        "first_name": new_profile.first_name,
        "last_name": new_profile.last_name,
        "email": new_profile.email,
        "phone_number": new_profile.phone_number,
        "role": new_profile.role,
        "plant_id": new_profile.plant_id,
        "dept_id": new_profile.dept_id,
        "assigned_zone_id": new_profile.assigned_zone_id,
        "assigned_zone_name": assigned_zone_name,
        "avatar_url": new_profile.avatar_url,
        "is_active": new_profile.is_active,
        "active_tasks_count": 0,
        "completed_tasks_count": 0,
        "created_at": new_profile.created_at
    }


@router.put("/zonal-leaders/{leader_id}", response_model=ZonalLeaderResponse)
async def update_zonal_leader(leader_id: str, payload: ZonalLeaderUpdate, actor: Actor = Depends(get_actor), db: AsyncSession = Depends(get_db)):
    """Management edits a Zonal Leader, reassigns zone, or toggles status."""
    res = await db.execute(select(Profile).where(Profile.id == leader_id))
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Zonal leader not found.")
        
    if payload.first_name:
        profile.first_name = payload.first_name
    if payload.last_name:
        profile.last_name = payload.last_name
    if payload.email:
        profile.email = payload.email
    if payload.phone_number is not None:
        profile.phone_number = payload.phone_number
    if payload.role:
        if payload.role not in ["zonal_leader", "operator", "supervisor", "auditor"]:
            raise HTTPException(403, "This role cannot be granted through people management")
        profile.role = payload.role
    if payload.is_active is not None:
        profile.is_active = payload.is_active
        
    # Reassign zone if changed
    if payload.assigned_zone_id is not None:
        if payload.assigned_zone_id == "" or payload.assigned_zone_id == "unassigned":
            # Unlink previous zone if any
            if profile.assigned_zone_id:
                prev_z = await db.execute(select(Zone).where(Zone.id == profile.assigned_zone_id))
                pz = prev_z.scalar_one_or_none()
                if pz and pz.leader_id == profile.id:
                    pz.leader_id = None
                    pz.leader_name = None
            profile.assigned_zone_id = None
            profile.assigned_zone_name = None
        elif payload.assigned_zone_id != profile.assigned_zone_id:
            z_res = await db.execute(select(Zone).where(Zone.id == payload.assigned_zone_id))
            new_zone = z_res.scalar_one_or_none()
            if new_zone:
                previous = await db.get(Zone, profile.assigned_zone_id) if profile.assigned_zone_id else None
                if previous and previous.leader_id == profile.id:
                    previous.leader_id = None
                    previous.leader_name = None
                profile.assigned_zone_id = new_zone.id
                profile.assigned_zone_name = new_zone.name
                new_zone.leader_id = profile.id
                new_zone.leader_name = f"{profile.first_name} {profile.last_name}"
            
    await db.commit()
    await db.refresh(profile)
    
    # Task counts
    active_cnt = await db.execute(
        select(func.count(Activity.id)).where(
            and_(
                Activity.assigned_to == profile.id,
                Activity.status.in_([ActivityStatus.ASSIGNED.value, ActivityStatus.IN_PROGRESS.value, ActivityStatus.SUBMITTED_FOR_REVIEW.value])
            )
        )
    )
    comp_cnt = await db.execute(
        select(func.count(Activity.id)).where(
            and_(
                Activity.assigned_to == profile.id,
                Activity.status.in_([ActivityStatus.APPROVED.value, ActivityStatus.COMPLETED.value])
            )
        )
    )
    
    return {
        "id": profile.id,
        "first_name": profile.first_name,
        "last_name": profile.last_name,
        "email": profile.email,
        "phone_number": profile.phone_number,
        "role": profile.role,
        "plant_id": profile.plant_id,
        "dept_id": profile.dept_id,
        "assigned_zone_id": profile.assigned_zone_id,
        "assigned_zone_name": profile.assigned_zone_name,
        "avatar_url": profile.avatar_url,
        "is_active": profile.is_active,
        "active_tasks_count": active_cnt.scalar() or 0,
        "completed_tasks_count": comp_cnt.scalar() or 0,
        "created_at": profile.created_at
    }


@router.delete("/zonal-leaders/{leader_id}")
async def delete_zonal_leader(leader_id: str, actor: Actor = Depends(get_actor), db: AsyncSession = Depends(get_db)):
    """Deactivate an operational account while retaining audit history."""
    res = await db.execute(select(Profile).where(Profile.id == leader_id))
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Zonal leader not found.")

    # 1. Unlink any zones that reference this leader
    zones_res = await db.execute(select(Zone).where(Zone.leader_id == leader_id))
    for z in zones_res.scalars().all():
        z.leader_id = None
        z.leader_name = None

    # Deactivate rather than erase authorship, historical assignments, or audit evidence.
    profile.is_active = False
    await db.commit()
    return {"message": f"{profile.first_name} {profile.last_name} deactivated; historical records retained", "deactivated_id": leader_id}
