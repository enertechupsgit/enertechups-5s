"""Server-side permissions and plant/zone/ownership scope for every business route."""
from dataclasses import dataclass
from datetime import datetime
import hashlib
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.models import Profile, Plant, Department, Zone, Activity, Asset, RedTag, WorkspaceSession

READ = {"overview.read", "work.read", "audit.read", "redtag.read", "asset.read", "location.read", "standard.read", "report.export", "access.read"}
PERMISSIONS = {
    "director": READ | {"people.read"},
    "supervisor": READ | {"people.read", "people.manage", "work.create", "work.execute", "work.review", "work.comment", "audit.execute", "redtag.create", "redtag.dispose", "asset.manage", "location.manage"},
    "auditor": READ | {"audit.execute", "work.comment", "redtag.create"},
    "zonal_leader": READ | {"work.create", "work.execute", "work.comment", "redtag.create"},
}
ROLE_NAMES = {"management": "director", "plant_manager": "supervisor", "super_admin": "supervisor", "operator": "zonal_leader"}

@dataclass
class Actor:
    profile: Profile
    role: str
    plant_ids: list[str]

    @property
    def limited(self):
        return self.role == "zonal_leader"

    @property
    def name(self):
        return f"{self.profile.first_name} {self.profile.last_name}"

    @property
    def permissions(self):
        return PERMISSIONS.get(self.role, set())

    def require(self, permission):
        if permission not in self.permissions:
            raise HTTPException(403, "Your role does not allow this action")

    def require_plant(self, plant_id):
        if plant_id not in self.plant_ids:
            raise HTTPException(403, "This plant is outside your assigned scope")

    def require_zone(self, zone_id):
        if self.limited and (not self.profile.assigned_zone_id or zone_id != self.profile.assigned_zone_id):
            raise HTTPException(403, "This zone is outside your assigned scope")

    def require_work(self, work):
        self.require_plant(work.plant_id)
        if self.limited and (work.assigned_to != self.profile.id or work.zone_id != self.profile.assigned_zone_id):
            raise HTTPException(403, "This work order is outside your assigned scope")

def scope_query(query, model, actor):
    query = query.where(model.plant_id.in_(actor.plant_ids))
    if actor.limited:
        if model is Activity:
            query = query.where(Activity.assigned_to == actor.profile.id)
        query = query.where(model.zone_id == actor.profile.assigned_zone_id) if actor.profile.assigned_zone_id else query.where(False)
    return query

async def get_actor(request: Request, db: AsyncSession = Depends(get_db)) -> Actor:
    token = request.cookies.get("enertech_session")
    authorization = request.headers.get("authorization", "")
    if authorization.startswith("Bearer "):
        token = authorization[7:]
    if not token:
        raise HTTPException(401, "Sign in to access the workspace")
    session = (await db.execute(select(WorkspaceSession).where(WorkspaceSession.token_hash == hashlib.sha256(token.encode()).hexdigest(), WorkspaceSession.expires_at > datetime.utcnow()))).scalar_one_or_none()
    profile = await db.get(Profile, session.profile_id) if session else None
    if not profile or not profile.is_active:
        raise HTTPException(401, "Your session has expired or access was revoked")
    role = ROLE_NAMES.get(profile.role, profile.role)
    if role not in PERMISSIONS:
        raise HTTPException(403, "No workspace permissions are configured for this role")
    plant = await db.get(Plant, profile.plant_id) if profile.plant_id else None
    if not plant:
        raise HTTPException(403, "Assign this account to a plant before signing in")
    plant_ids = [plant.id]
    if role == "director":
        plant_ids = list((await db.execute(select(Plant.id).where(Plant.org_id == plant.org_id, Plant.is_active == True))).scalars())
    return Actor(profile, role, plant_ids)

def validate_origin(request):
    origin = request.headers.get("origin")
    if origin and origin not in {"http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:8000", "http://localhost:8000"}:
        from app.core.config import settings
        if origin not in [value for value in settings.CORS_ORIGINS if value != "*"]:
            raise HTTPException(403, "This request origin is not allowed")

async def enforce_access(request: Request, actor: Actor = Depends(get_actor), db: AsyncSession = Depends(get_db)):
    path = request.url.path.split("/api/v1", 1)[-1]
    method = request.method
    if method not in {"GET", "HEAD", "OPTIONS"}:
        validate_origin(request)
        if not request.headers.get("x-workspace-request"):
            raise HTTPException(403, "A workspace request header is required")
    family = path.split("/")[1]
    if method == "GET":
        permission = {"plants": "location.read", "activities": "work.read", "audits": "audit.read", "redtags": "redtag.read", "assets": "asset.read", "management": "people.read", "reports": "report.export"}.get(family)
    else:
        permission = {"plants": "location.manage", "audits": "audit.execute", "redtags": "redtag.create" if method == "POST" else "redtag.dispose", "assets": "asset.manage", "management": "people.manage"}.get(family)
        if family == "activities":
            permission = "work.review" if path.endswith("/review") else "work.comment" if path.endswith("/comments") else "work.create" if path == "/activities" else "work.execute"
    if not permission:
        raise HTTPException(403, "No access policy is configured for this operation")
    actor.require(permission)
    if family == "plants" and method == "DELETE":
        raise HTTPException(409, "Locations with historical records must be archived through a retention workflow, not deleted")
    if method == "POST" and family == "activities" and path.endswith("/submit"):
        raise HTTPException(409, "Use report submission with corrective action and after evidence")
    for key, model in [("activity_id", Activity), ("asset_id", Asset), ("tag_id", RedTag), ("leader_id", Profile), ("zone_id", Zone), ("dept_id", Department)]:
        record_id = request.path_params.get(key)
        if not record_id:
            continue
        record = await db.get(model, record_id)
        if not record:
            raise HTTPException(404, "Record not found")
        if isinstance(record, Activity):
            actor.require_work(record)
            if method == "PUT" and record.status in {"completed", "approved"}:
                raise HTTPException(409, "Completed work is a retained record and cannot be edited")
            if path.endswith("/review") and record.assigned_to == actor.profile.id:
                raise HTTPException(403, "You cannot approve or reject your own submitted work")
        elif isinstance(record, Zone):
            parent = await db.get(Department, record.dept_id)
            actor.require_plant(parent.plant_id)
            actor.require_zone(record.id)
        else:
            actor.require_plant(record.plant_id)
            if isinstance(record, Profile) and method != "GET":
                if record.role not in {"zonal_leader", "operator", "auditor", "supervisor"}:
                    raise HTTPException(403, "This account cannot be managed by an operational supervisor")
                if method == "DELETE" and record.id == actor.profile.id:
                    raise HTTPException(403, "You cannot deactivate your own session account")
            if hasattr(record, "zone_id"):
                actor.require_zone(record.zone_id)
    plant_param = request.path_params.get("plant_id") or request.query_params.get("plant_id")
    if plant_param:
        actor.require_plant(plant_param)
    if request.query_params.get("zone_id"):
        actor.require_zone(request.query_params["zone_id"])
    if method in {"POST", "PUT", "PATCH"} and request.headers.get("content-type", "").startswith("application/json"):
        payload = await request.json()
        if isinstance(payload, dict):
            if payload.get("plant_id"):
                actor.require_plant(payload["plant_id"])
            if payload.get("dept_id"):
                department = await db.get(Department, payload["dept_id"])
                if not department:
                    raise HTTPException(422, "Department not found")
                actor.require_plant(department.plant_id)
                if payload.get("plant_id") and department.plant_id != payload["plant_id"]:
                    raise HTTPException(422, "Department must belong to the selected plant")
            zone_id = payload.get("zone_id") or payload.get("assigned_zone_id")
            if zone_id:
                actor.require_zone(zone_id)
                zone = await db.get(Zone, zone_id)
                parent = await db.get(Department, zone.dept_id) if zone else None
                if not parent or parent.plant_id not in actor.plant_ids or (payload.get("plant_id") and payload["plant_id"] != parent.plant_id):
                    raise HTTPException(422, "Zone must belong to the selected plant")
            if actor.limited and family == "activities" and path == "/activities":
                if payload.get("assigned_to") != actor.profile.id or zone_id != actor.profile.assigned_zone_id:
                    raise HTTPException(403, "Create actions for yourself in your assigned zone")
            if family == "activities" and payload.get("assigned_to"):
                assignee = await db.get(Profile, payload["assigned_to"])
                if not assignee or not assignee.is_active or assignee.plant_id not in actor.plant_ids or (payload.get("plant_id") and assignee.plant_id != payload["plant_id"]):
                    raise HTTPException(422, "Assignee must be an active member of the selected plant")
            if actor.limited and method == "PUT" and family == "activities":
                raise HTTPException(403, "Use the task execution and report submission actions")
    request.state.actor = actor
