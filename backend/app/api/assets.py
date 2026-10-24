from typing import Literal, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.models import Asset, AssetStatusEvent, Plant, Zone, Department

from app.core.access import Actor, get_actor, scope_query

router = APIRouter(prefix="/assets", tags=["Assets"])

class AssetCreate(BaseModel):
    model_config = {"str_strip_whitespace": True}
    plant_id: str
    zone_id: Optional[str] = None
    parent_id: Optional[str] = None
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=100)
    description: Optional[str] = None
    manufacturer: Optional[str] = None
    model: Optional[str] = None
    status: Literal["online", "offline", "maintenance"] = "online"

class StatusChange(BaseModel):
    model_config = {"str_strip_whitespace": True}
    status: Literal["online", "offline", "maintenance"]
    note: str = Field(min_length=1, max_length=2000)

async def serialize(asset, db):
    events = (await db.execute(select(AssetStatusEvent).where(AssetStatusEvent.asset_id == asset.id).order_by(AssetStatusEvent.created_at.desc()))).scalars().all()
    return {**{column.name: getattr(asset, column.name) for column in Asset.__table__.columns}, "events": [{"id": event.id, "status": event.status, "note": event.note, "created_at": event.created_at} for event in events]}

@router.get("")
async def list_assets(plant_id: str, actor: Actor = Depends(get_actor), db: AsyncSession = Depends(get_db)):
    assets = (await db.execute(scope_query(select(Asset).where(Asset.plant_id == plant_id).order_by(Asset.name), Asset, actor))).scalars().all()
    return [await serialize(asset, db) for asset in assets]

@router.post("")
async def create_asset(payload: AssetCreate, actor: Actor = Depends(get_actor), db: AsyncSession = Depends(get_db)):
    if not await db.get(Plant, payload.plant_id):
        raise HTTPException(404, "Plant not found")
    if (await db.execute(select(Asset).where(Asset.code == payload.code.strip()))).scalar_one_or_none():
        raise HTTPException(409, "An asset with this code already exists")
    if payload.parent_id:
        parent = await db.get(Asset, payload.parent_id)
        if not parent or parent.plant_id != payload.plant_id:
            raise HTTPException(422, "Parent asset must belong to the same plant")
    if payload.zone_id:
        zone = await db.get(Zone, payload.zone_id)
        department = await db.get(Department, zone.dept_id) if zone else None
        if not department or department.plant_id != payload.plant_id:
            raise HTTPException(422, "Zone must belong to the selected plant")
    if not payload.name.strip() or not payload.code.strip():
        raise HTTPException(422, "Name and asset code are required")
    asset = Asset(**payload.model_dump())
    asset.name, asset.code = asset.name.strip(), asset.code.strip()
    db.add(asset)
    await db.flush()
    db.add(AssetStatusEvent(asset_id=asset.id, status=asset.status, note="Asset registered"))
    await db.commit()
    return await serialize(asset, db)

@router.post("/{asset_id}/status")
async def update_status(asset_id: str, payload: StatusChange, actor: Actor = Depends(get_actor), db: AsyncSession = Depends(get_db)):
    asset = await db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(404, "Asset not found")
    if not payload.note.strip():
        raise HTTPException(422, "A reason is required")
    if asset.status != payload.status:
        asset.status = payload.status
        db.add(AssetStatusEvent(asset_id=asset.id, status=payload.status, note=payload.note.strip()))
        await db.commit()
    return await serialize(asset, db)
