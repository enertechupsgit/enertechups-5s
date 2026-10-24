"""Integration checks use a disposable database, never the local plant databases."""
import unittest
import os
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.main import app
from app.core.database import Base, get_db
from app.models.models import Organization, Plant, Department, Zone, Profile, Activity


class WorkspaceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.demo_environment = patch.dict(os.environ, {"LOCAL_DEMO": "1"})
        self.demo_environment.start()
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

        async def dependency():
            async with self.sessions() as session:
                yield session

        app.dependency_overrides[get_db] = dependency
        async with self.sessions() as session:
            org = Organization(name="Test organization", slug="isolated-test")
            session.add(org)
            await session.flush()
            plant = Plant(org_id=org.id, name="Test plant", code="TEST")
            session.add(plant)
            await session.flush()
            dept = Department(plant_id=plant.id, name="Assembly", code="ASM")
            session.add(dept)
            await session.flush()
            zone = Zone(dept_id=dept.id, name="Workbench", code="WB")
            session.add(zone)
            await session.commit()
            self.plant_id, self.zone_id = plant.id, zone.id
            supervisor = Profile(first_name="Test", last_name="Supervisor", email="supervisor@sample.example", role="supervisor", plant_id=plant.id)
            session.add(supervisor)
            await session.commit()
            self.supervisor_id = supervisor.id
        self.client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api/v1", headers={"X-Workspace-Request":"1"})
        response = await self.client.post("/auth/local-session", json={"profile_id":self.supervisor_id})
        self.assertEqual(response.status_code,200,response.text)

    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        await self.engine.dispose()
        self.demo_environment.stop()

    async def create_work(self):
        response = await self.client.post("/activities", json={"plant_id": self.plant_id, "zone_id": self.zone_id, "title": "Organize tools", "problem_description": "Tools need designated positions"})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def test_start_submit_rework_and_complete_survives_read(self):
        work = await self.create_work()
        url = f"/activities/{work['id']}"
        response = await self.client.post(url + "/start")
        self.assertEqual(response.json()["status"], "in_progress")
        self.assertEqual((await self.client.post(url + "/start")).status_code, 409)
        self.assertEqual((await self.client.post(url + "/report", json={"corrective_action": "Updated"})).status_code, 422)
        report = {"corrective_action": "Marked tool positions", "after_photo_url": "data:image/png;base64,aGVsbG8="}
        response = await self.client.post(url + "/report", json=report)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "submitted_for_review")
        self.assertEqual(len(response.json()["evidence"]), 1)
        self.assertEqual((await self.client.post(url + "/review", json={"decision": "reject"})).status_code, 400)
        response = await self.client.post(url + "/review", json={"decision": "reject", "rejection_reason": "Label the return outlines"})
        self.assertEqual(response.json()["status"], "rejected")
        await self.client.post(url + "/start")
        await self.client.post(url + "/report", json=report)
        response = await self.client.post(url + "/review", json={"decision": "approve"})
        self.assertEqual(response.json()["status"], "completed")
        reread = (await self.client.get(url)).json()
        self.assertEqual(reread["status"], "completed")
        self.assertEqual(reread["corrective_action"], "Marked tool positions")
        self.assertGreaterEqual(len(reread["history"]), 7)
        self.assertEqual((await self.client.post(url + "/review", json={"decision": "approve"})).status_code, 409)
        pdf = await self.client.get(f"/reports/activity/{work['id']}/pdf")
        self.assertEqual(pdf.status_code, 200)
        self.assertTrue(pdf.content.startswith(b"%PDF"))

    async def test_assets_persist_status_events_and_validate_parent(self):
        payload = {"plant_id": self.plant_id, "zone_id": self.zone_id, "name": "Test bench", "code": "TEST-001"}
        response = await self.client.post("/assets", json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        asset = response.json()
        self.assertEqual(len(asset["events"]), 1)
        self.assertEqual((await self.client.post("/assets", json=payload)).status_code, 409)
        self.assertEqual((await self.client.post("/assets", json={**payload, "code": "TEST-002", "parent_id": "missing"})).status_code, 422)
        response = await self.client.post(f"/assets/{asset['id']}/status", json={"status": "maintenance", "note": "Scheduled inspection"})
        self.assertEqual(response.status_code, 200, response.text)
        reread = (await self.client.get("/assets", params={"plant_id": self.plant_id})).json()[0]
        self.assertEqual(reread["status"], "maintenance")
        self.assertEqual(len(reread["events"]), 2)
        self.assertEqual((await self.client.post(f"/assets/{asset['id']}/status", json={"status": "online", "note": ""})).status_code, 422)

    async def test_audits_validate_score_and_zone(self):
        payload = {"plant_id": self.plant_id, "zone_id": self.zone_id, "zone_name": "Untrusted display name", "sort_score": 80, "set_in_order_score": 90, "shine_score": 100, "standardize_score": 75, "sustain_score": 85}
        self.assertEqual((await self.client.post("/audits", json={**payload, "sort_score": 101})).status_code, 422)
        self.assertEqual((await self.client.post("/audits", json={**payload, "zone_id": "missing"})).status_code, 422)
        response = await self.client.post("/audits", json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["score_percentage"], 86)
        self.assertEqual(response.json()["zone_name"], "Workbench")

    async def add_identity(self, role, first, zone_id=None):
        async with self.sessions() as session:
            person = Profile(first_name=first, last_name="Tester", email=f"{first.lower()}@sample.example", role=role, plant_id=self.plant_id, assigned_zone_id=zone_id, assigned_zone_name="Workbench" if zone_id else None)
            session.add(person)
            await session.commit()
            return person.id

    async def test_director_reads_but_cannot_mutate(self):
        director = await self.add_identity("management", "Director")
        response = await self.client.post("/auth/local-session",json={"profile_id":director})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()["role"],"director")
        self.assertEqual((await self.client.get("/plants")).status_code,200)
        self.assertEqual((await self.client.get("/management/zonal-leaders")).status_code,200)
        self.assertEqual((await self.client.post("/activities",json={"plant_id":self.plant_id,"zone_id":self.zone_id,"title":"Forbidden","problem_description":"Forbidden"})).status_code,403)
        self.assertEqual((await self.client.post("/assets",json={"plant_id":self.plant_id,"name":"Forbidden","code":"FORBID"})).status_code,403)
        self.assertEqual((await self.client.get("/activities",headers={"Authorization":"Bearer fabricated-token"})).status_code,401)

    async def test_zonal_scope_and_denied_actions(self):
        leader = await self.add_identity("zonal_leader", "Leader", self.zone_id)
        other = await self.add_identity("zonal_leader", "Other", self.zone_id)
        async with self.sessions() as session:
            department = (await session.get(Zone,self.zone_id)).dept_id
            second = Zone(dept_id=department,name="Other zone",code="OTHER")
            session.add(second)
            await session.flush()
            own = Activity(plant_id=self.plant_id,zone_id=self.zone_id,activity_number="OWN",title="Own action",problem_description="Own",assigned_to=leader,status="in_progress")
            others = Activity(plant_id=self.plant_id,zone_id=second.id,activity_number="OTHER",title="Other action",problem_description="Other",assigned_to=other,status="submitted_for_review")
            session.add_all([own,others])
            await session.commit()
            own_id, other_id, other_zone = own.id,others.id,second.id
        await self.client.post("/auth/local-session",json={"profile_id":leader})
        response = await self.client.get("/activities",params={"plant_id":self.plant_id})
        self.assertEqual([a["id"] for a in response.json()],[own_id])
        self.assertEqual((await self.client.get(f"/activities/{other_id}")).status_code,403)
        self.assertEqual((await self.client.get(f"/reports/activity/{other_id}/pdf")).status_code,403)
        self.assertEqual((await self.client.post(f"/activities/{own_id}/review",json={"decision":"approve"})).status_code,403)
        self.assertEqual((await self.client.post("/assets",json={"plant_id":self.plant_id,"code":"NO","name":"NO"})).status_code,403)
        self.assertEqual((await self.client.get("/management/zonal-leaders")).status_code,403)
        self.assertEqual((await self.client.post("/activities",json={"plant_id":self.plant_id,"zone_id":other_zone,"assigned_to":leader,"title":"No","problem_description":"No"})).status_code,403)
        plants=(await self.client.get("/plants")).json()
        self.assertEqual([z["id"] for p in plants for d in p["departments"] for z in d["zones"]],[self.zone_id])
        comment=await self.client.post(f"/activities/{own_id}/comments",json={"comment":"Update","author_name":"Spoofed director"})
        self.assertEqual(comment.status_code,200,comment.text)
        self.assertEqual(comment.json()["author_name"],"Leader Tester")
        self.assertEqual((await self.client.post(f"/activities/{own_id}/submit",json={})).status_code,409)

    async def test_self_review_and_cross_organization_are_blocked(self):
        async with self.sessions() as session:
            own=Activity(plant_id=self.plant_id,zone_id=self.zone_id,activity_number="SELF",title="Self",problem_description="Self",assigned_to=self.supervisor_id,status="submitted_for_review")
            org=Organization(name="Other organization",slug="other-org")
            session.add_all([own,org]);await session.flush()
            plant=Plant(org_id=org.id,name="Other plant",code="OTHER")
            session.add(plant);await session.commit();own_id,other_id=own.id,plant.id
        self.assertEqual((await self.client.post(f"/activities/{own_id}/review",json={"decision":"approve"})).status_code,403)
        self.assertEqual((await self.client.get("/activities",params={"plant_id":other_id})).status_code,403)
        self.assertNotIn(other_id,[p["id"] for p in (await self.client.get("/plants")).json()])

    async def test_auditor_permissions_and_revoked_membership(self):
        auditor = await self.add_identity("auditor", "Auditor")
        await self.client.post("/auth/local-session",json={"profile_id":auditor})
        payload={"plant_id":self.plant_id,"zone_id":self.zone_id,"zone_name":"Untrusted name","auditor_name":"Spoofed director","sort_score":90,"set_in_order_score":90,"shine_score":90,"standardize_score":90,"sustain_score":90}
        response=await self.client.post("/audits",json=payload)
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()["auditor_name"],"Auditor Tester")
        self.assertEqual((await self.client.post("/management/zonal-leaders",json={})).status_code,403)
        self.assertEqual((await self.client.post("/activities",json={"plant_id":self.plant_id,"zone_id":self.zone_id,"title":"No","problem_description":"No"})).status_code,403)
        async with self.sessions() as session:
            person=await session.get(Profile,auditor)
            person.is_active=False
            await session.commit()
        self.assertEqual((await self.client.get("/audits")).status_code,401)

    async def test_sessions_logout_csrf_and_non_demo_switch(self):
        self.assertEqual((await self.client.post("/auth/local-session",json={"profile_id":self.supervisor_id},headers={"Origin":"https://untrusted.example"})).status_code,403)
        with patch.dict(os.environ,{"LOCAL_DEMO":"0"}):
            self.assertEqual((await self.client.get("/auth/local-identities")).status_code,403)
            self.assertEqual((await self.client.post("/auth/local-session",json={"profile_id":self.supervisor_id})).status_code,403)
        self.assertEqual((await self.client.post("/auth/logout")).status_code,200)
        self.assertEqual((await self.client.get("/plants")).status_code,401)
        self.assertEqual((await self.client.get("/auth/me")).status_code,401)

    async def test_hosted_setup_password_login_and_lockout(self):
        from app.models.models import PasswordCredential
        from app.core.passwords import verify_password
        from app.api.auth import _attempts
        _attempts.clear()
        self.client.cookies.clear()
        self.client.base_url = "https://test/api/v1/"
        values={"LOCAL_DEMO":"0", "APP_ENV":"production", "BOOTSTRAP_TOKEN":"isolated-test-setup-token-123456789", "BOOTSTRAP_ADMIN_EMAIL":"marketing@enertechups.com", "RENDER_EXTERNAL_URL":"https://test"}
        payload={"email":"marketing@enertechups.com", "password":"Isolated-Test-Password-123!", "setup_token":values["BOOTSTRAP_TOKEN"]}
        with patch.dict(os.environ,values):
            self.assertTrue((await self.client.get("auth/status")).json()["setup_required"])
            self.assertEqual((await self.client.post("auth/setup",json={**payload,"setup_token":"wrong-token-123456"})).status_code,403)
            self.assertEqual((await self.client.post("auth/setup",json=payload,headers={"Origin":"https://evil.example"})).status_code,403)
            response=await self.client.post("auth/setup",json=payload,headers={"Origin":"https://test"})
            self.assertEqual(response.status_code,200,response.text)
            self.assertIn("Secure",response.headers["set-cookie"])
            self.assertIn("HttpOnly",response.headers["set-cookie"])
            owner=response.json()["id"]
            self.assertEqual(response.json()["role"],"supervisor")
            self.assertFalse((await self.client.get("auth/status")).json()["setup_required"])
            self.assertEqual((await self.client.post("auth/setup",json=payload)).status_code,409)
            self.assertEqual((await self.client.get("auth/local-identities")).status_code,403)
            self.assertEqual((await self.client.get("plants")).status_code,200)
            async with self.sessions() as session:
                saved=await session.get(PasswordCredential,owner)
                self.assertNotIn(payload["password"],saved.password_hash)
                self.assertTrue(verify_password(payload["password"],saved.password_hash))
            await self.client.post("auth/logout")
            self.assertEqual((await self.client.get("auth/me")).status_code,401)
            login={"email":payload["email"],"password":payload["password"]}
            self.assertEqual((await self.client.post("auth/login",json=login)).status_code,200)
            await self.client.post("auth/logout")
            for _ in range(5):
                self.assertEqual((await self.client.post("auth/login",json={**login,"password":"wrong"})).status_code,401)
            self.assertEqual((await self.client.post("auth/login",json=login)).status_code,429)
        _attempts.clear()

if __name__ == "__main__":
    unittest.main()
