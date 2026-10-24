"""Local sample identity switching is explicitly unavailable on non-demo servers."""
import hashlib
import os
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.access import Actor, get_actor, ROLE_NAMES, PERMISSIONS, validate_origin
from app.models.models import Profile, WorkspaceSession, AccessEvent

router = APIRouter(prefix="/auth", tags=["Identity and access"])

def local_only(request):
    if os.getenv("LOCAL_DEMO") != "1" or not request.client or request.client.host not in {"127.0.0.1", "::1", "testclient", "test"}:
        raise HTTPException(403, "Sample role switching is available only on a loopback local-preview server")
    validate_origin(request)

def identity(profile):
    role = ROLE_NAMES.get(profile.role, profile.role)
    return {"id": profile.id, "name": f"{profile.first_name} {profile.last_name}", "first_name": profile.first_name, "last_name": profile.last_name, "email": profile.email, "role": role, "plant_id": profile.plant_id, "zone_id": profile.assigned_zone_id, "zone_name": profile.assigned_zone_name, "permissions": sorted(PERMISSIONS.get(role, set()))}

@router.get("/local-identities")
async def local_identities(request: Request, db: AsyncSession = Depends(get_db)):
    local_only(request)
    profiles = (await db.execute(select(Profile).where(Profile.is_active == True).order_by(Profile.created_at))).scalars().all()
    return [identity(p) for p in profiles if p.email.endswith("@sample.example") and ROLE_NAMES.get(p.role, p.role) in PERMISSIONS]

class SwitchRequest(BaseModel):
    profile_id: str

@router.post("/local-session")
async def local_session(payload: SwitchRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    local_only(request)
    if request.headers.get("x-workspace-request") != "1":
        raise HTTPException(403, "A workspace request header is required")
    profile = await db.get(Profile, payload.profile_id)
    if not profile or not profile.is_active or not profile.email.endswith("@sample.example") or ROLE_NAMES.get(profile.role, profile.role) not in PERMISSIONS:
        raise HTTPException(403, "Choose an active local sample identity")
    previous = request.cookies.get("enertech_session")
    if previous:
        old = (await db.execute(select(WorkspaceSession).where(WorkspaceSession.token_hash == hashlib.sha256(previous.encode()).hexdigest()))).scalar_one_or_none()
        if old:
            await db.delete(old)
    token = secrets.token_urlsafe(32)
    db.add(WorkspaceSession(token_hash=hashlib.sha256(token.encode()).hexdigest(), profile_id=profile.id, expires_at=datetime.utcnow() + timedelta(hours=8)))
    db.add(AccessEvent(profile_id=profile.id, action="local_role_session_started", detail=ROLE_NAMES.get(profile.role, profile.role)))
    await db.commit()
    response.set_cookie("enertech_session", token, httponly=True, secure=request.url.scheme == "https", samesite="strict", max_age=8*3600, path="/api")
    response.headers["Cache-Control"] = "no-store"
    return identity(profile)

@router.get("/me")
async def me(response: Response, actor: Actor = Depends(get_actor)):
    response.headers["Cache-Control"] = "no-store"
    return identity(actor.profile)

@router.post("/logout")
async def logout(request: Request, response: Response, actor: Actor = Depends(get_actor), db: AsyncSession = Depends(get_db)):
    validate_origin(request)
    if request.headers.get("x-workspace-request") != "1":
        raise HTTPException(403, "A workspace request header is required")
    token = request.cookies.get("enertech_session", "")
    session = (await db.execute(select(WorkspaceSession).where(WorkspaceSession.token_hash == hashlib.sha256(token.encode()).hexdigest()))).scalar_one_or_none()
    if session:
        await db.delete(session)
    db.add(AccessEvent(profile_id=actor.profile.id, action="session_ended"))
    await db.commit()
    response.delete_cookie("enertech_session", path="/api")
    return {"signed_out": True}
