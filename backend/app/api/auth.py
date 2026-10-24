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

# Hosted account setup is protected by a Render-generated secret, never a public role switch.
from pydantic import Field
from sqlalchemy import func, text
from app.models.models import PasswordCredential, Plant
from app.core.passwords import hash_password, verify_password
import hmac
import asyncio
from collections import OrderedDict
from time import monotonic

_attempts = OrderedDict()

def auth_request(request):
    validate_origin(request)
    if request.headers.get("x-workspace-request") != "1":
        raise HTTPException(403, "A workspace request header is required")
    key = request.client.host if request.client else "unknown"
    now = monotonic()
    count, deadline = _attempts.get(key, (0, now + 600))
    if now >= deadline:
        count, deadline = 0, now + 600
    if count >= 30:
        raise HTTPException(429, "Too many sign-in attempts. Try again in ten minutes.")
    _attempts[key] = (count + 1, deadline)
    if len(_attempts) > 10000:
        _attempts.popitem(last=False)

class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=256)

class SetupRequest(LoginRequest):
    setup_token: str = Field(min_length=16, max_length=256)
    password: str = Field(min_length=12, max_length=256)

async def has_password_account(db):
    return bool(await db.scalar(select(func.count()).select_from(PasswordCredential)))

@router.get("/status")
async def auth_status(response: Response, db: AsyncSession = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store"
    return {"setup_required": bool(os.getenv("BOOTSTRAP_TOKEN")) and not await has_password_account(db), "password_login": True}

async def password_session(profile, request, response, db, action):
    previous = request.cookies.get("enertech_session")
    if previous:
        old = (await db.execute(select(WorkspaceSession).where(WorkspaceSession.token_hash == hashlib.sha256(previous.encode()).hexdigest()))).scalar_one_or_none()
        if old:
            await db.delete(old)
    token = secrets.token_urlsafe(32)
    db.add(WorkspaceSession(token_hash=hashlib.sha256(token.encode()).hexdigest(), profile_id=profile.id, expires_at=datetime.utcnow()+timedelta(hours=8)))
    db.add(AccessEvent(profile_id=profile.id, action=action))
    await db.commit()
    response.set_cookie("enertech_session", token, httponly=True, secure=os.getenv("APP_ENV") == "production" or request.url.scheme == "https", samesite="strict", max_age=8*3600, path="/api")
    response.headers["Cache-Control"] = "no-store"
    return identity(profile)

@router.post("/setup")
async def setup(payload: SetupRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    auth_request(request)
    expected = os.getenv("BOOTSTRAP_TOKEN", "")
    if not expected or not hmac.compare_digest(payload.setup_token, expected):
        raise HTTPException(403, "Invalid setup token")
    # Serialize first-owner creation across workers on PostgreSQL.
    if db.bind.dialect.name == "postgresql":
        await db.execute(text("SELECT pg_advisory_xact_lock(532026)"))
    if await has_password_account(db):
        raise HTTPException(409, "Workspace setup is already complete. Sign in instead.")
    email = payload.email.strip().lower()
    if email != os.getenv("BOOTSTRAP_ADMIN_EMAIL", "marketing@enertechups.com").strip().lower():
        raise HTTPException(403, "Use the administrator email configured for this deployment")
    plant = (await db.execute(select(Plant).where(Plant.is_active == True).order_by(Plant.created_at))).scalars().first()
    if not plant:
        raise HTTPException(503, "Workspace initialization is not complete")
    profile = (await db.execute(select(Profile).where(func.lower(Profile.email) == email))).scalar_one_or_none()
    if profile and (not profile.is_active or profile.plant_id != plant.id):
        raise HTTPException(403, "The configured account is not eligible for initial setup")
    if not profile:
        profile = Profile(email=email, first_name="EnerTech", last_name="Administrator", role="supervisor", plant_id=plant.id)
        db.add(profile)
        await db.flush()
    profile.role = "supervisor"
    encoded = await asyncio.to_thread(hash_password, payload.password)
    db.add(PasswordCredential(profile_id=profile.id, password_hash=encoded))
    return await password_session(profile, request, response, db, "initial_administrator_created")

@router.post("/login")
async def login(payload: LoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    auth_request(request)
    profile = (await db.execute(select(Profile).where(func.lower(Profile.email) == payload.email.strip().lower()))).scalar_one_or_none()
    credential = await db.get(PasswordCredential, profile.id) if profile else None
    now = datetime.utcnow()
    from app.models.models import TestAccountMembership
    test_member = await db.get(TestAccountMembership, profile.id) if profile else None
    if test_member and test_member.expires_at <= now:
        raise HTTPException(401, "This testing account has expired")
    if credential and credential.locked_until and credential.locked_until > now:
        raise HTTPException(429, "Account temporarily locked. Try again in fifteen minutes.")
    # A fixed dummy hash makes unknown accounts use the same expensive password operation.
    encoded = credential.password_hash if credential else "scrypt$00000000000000000000000000000000$" + "0"*128
    verified = await asyncio.to_thread(verify_password, payload.password, encoded)
    if not credential or not verified or not profile.is_active or ROLE_NAMES.get(profile.role,profile.role) not in PERMISSIONS:
        if credential:
            credential.failed_attempts += 1
            if credential.failed_attempts >= 5:
                credential.locked_until = now + timedelta(minutes=15)
                credential.failed_attempts = 0
            db.add(AccessEvent(profile_id=profile.id, action="password_login_failed"))
            await db.commit()
        raise HTTPException(401, "Email or password is incorrect")
    if not profile.plant_id:
        raise HTTPException(403, "This account has no plant assignment")
    credential.failed_attempts = 0
    credential.locked_until = None
    return await password_session(profile, request, response, db, "password_session_started")

from app.models.models import Organization, Department, Zone, TestAccountMembership, Activity

async def test_account_owner(actor, db):
    email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "marketing@enertechups.com").strip().lower()
    credential = await db.get(PasswordCredential, actor.profile.id)
    member = await db.get(TestAccountMembership, actor.profile.id)
    if actor.profile.email.lower() != email or actor.role not in {"supervisor", "admin"} or not credential or member:
        raise HTTPException(403, "Only the configured workspace owner can provision testing accounts")

@router.get("/test-accounts/status")
async def test_accounts_status(response: Response, actor: Actor = Depends(get_actor), db: AsyncSession = Depends(get_db)):
    await test_account_owner(actor, db)
    response.headers["Cache-Control"] = "no-store"
    count = await db.scalar(select(func.count()).select_from(TestAccountMembership).where(TestAccountMembership.owner_id == actor.profile.id))
    return {"can_create": not bool(count), "existing_count": count}

@router.post("/test-accounts")
async def create_test_accounts(request: Request, response: Response, actor: Actor = Depends(get_actor), db: AsyncSession = Depends(get_db)):
    validate_origin(request)
    if request.headers.get("x-workspace-request") != "1":
        raise HTTPException(403, "A workspace request header is required")
    await test_account_owner(actor, db)
    if db.bind.dialect.name == "postgresql":
        await db.execute(text("SELECT pg_advisory_xact_lock(532027)"))
    existing = await db.scalar(select(func.count()).select_from(TestAccountMembership).where(TestAccountMembership.owner_id == actor.profile.id))
    if existing:
        raise HTTPException(409, "Test accounts already exist. Passwords are shown only at creation and cannot be retrieved.")
    org = Organization(name="EnerTech — Isolated Testing", slug=f"test-accounts-{actor.profile.id}")
    db.add(org)
    await db.flush()
    plant = Plant(org_id=org.id, name="EnerTech Test Plant", code="ET-TEST", location="Testing only")
    db.add(plant)
    await db.flush()
    department = Department(plant_id=plant.id, name="Test Department", code="TEST")
    db.add(department)
    await db.flush()
    zones = []
    for number in range(1,4):
        zone = Zone(dept_id=department.id, name=f"Test Zone {number}", code=f"TEST-Z{number}", current_score=0)
        db.add(zone)
        zones.append(zone)
    await db.flush()
    expires = datetime.utcnow() + timedelta(days=7)
    definitions = [("Management", "director", None), ("HR", "hr", None), ("Zone Leader 1", "zonal_leader", zones[0]), ("Zone Leader 2", "zonal_leader", zones[1]), ("Zone Leader 3", "zonal_leader", zones[2]), ("Admin", "admin", None)]
    accounts = []
    for index, (name, role, zone) in enumerate(definitions):
        local_name = ["management", "hr", "zone1", "zone2", "zone3", "admin"][index]
        email = f"{local_name}.{actor.profile.id[:8]}@testing.enertech.example"
        password = "Et5s!" + secrets.token_urlsafe(18)
        person = Profile(first_name=name, last_name="Test", email=email, role=role, plant_id=plant.id, assigned_zone_id=zone.id if zone else None, assigned_zone_name=zone.name if zone else None)
        db.add(person)
        await db.flush()
        db.add(PasswordCredential(profile_id=person.id, password_hash=await asyncio.to_thread(hash_password,password)))
        db.add(TestAccountMembership(profile_id=person.id, owner_id=actor.profile.id, expires_at=expires))
        if zone:
            zone.leader_id, zone.leader_name = person.id, f"{name} Test"
            db.add(Activity(plant_id=plant.id, zone_id=zone.id, activity_number=f"TEST-{person.id[:12]}", title=f"Test workplace organization in {zone.name}", problem_description="Synthetic testing task. Inspect the designated storage layout and submit an improvement with evidence.", assigned_to=person.id, created_by=actor.profile.id, status="assigned", category="sort_seiri"))
        accounts.append({"name":name,"role":role,"email":email,"password":password,"zone":zone.name if zone else "Test plant","expires_at":expires.isoformat()+"Z"})
    db.add(AccessEvent(profile_id=actor.profile.id,action="isolated_test_accounts_created",detail=f"Six accounts in test plant {plant.id}; expire {expires.isoformat()}Z"))
    await db.commit()
    response.headers["Cache-Control"] = "no-store"
    return {"accounts":accounts,"plant_id":plant.id,"expires_at":expires.isoformat()+"Z"}
