"""Integration checks use a disposable database, never the local plant databases."""
import unittest
import os
import base64, io
from PIL import Image
_photo = io.BytesIO()
Image.new("RGB", (16,16), "#1d359d").save(_photo,format="PNG")
PHOTO = "data:image/png;base64," + base64.b64encode(_photo.getvalue()).decode()
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
        report = {"corrective_action": "Marked tool positions", "after_photo_url": PHOTO}
        response = await self.client.post(url + "/report", json=report)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["status"], "submitted_for_review")
        self.assertEqual(len(response.json()["evidence"]), 1)
        reviewer = await self.add_identity("supervisor", "IndependentReviewer")
        await self.client.post("/auth/local-session", json={"profile_id":reviewer})
        self.assertEqual((await self.client.post(url + "/review", json={"decision": "reject"})).status_code, 400)
        response = await self.client.post(url + "/review", json={"decision": "reject", "rejection_reason": "Label the return outlines"})
        self.assertEqual(response.json()["status"], "rejected")
        await self.client.post("/auth/local-session", json={"profile_id":self.supervisor_id})
        await self.client.post(url + "/start")
        await self.client.post(url + "/report", json=report)
        await self.client.post("/auth/local-session", json={"profile_id":reviewer})
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

    async def test_six_isolated_test_accounts_and_expiry(self):
        from app.api.auth import _attempts
        from app.models.models import TestAccountMembership
        from datetime import datetime, timedelta
        _attempts.clear()
        self.assertEqual((await self.client.post("/auth/test-accounts",json={})).status_code,403)
        values={"LOCAL_DEMO":"0", "BOOTSTRAP_TOKEN":"isolated-test-owner-token-123456789", "BOOTSTRAP_ADMIN_EMAIL":"marketing@enertechups.com"}
        with patch.dict(os.environ,values):
            setup=await self.client.post("/auth/setup",json={"email":"marketing@enertechups.com","password":"Isolated-Owner-Password-123!","setup_token":values["BOOTSTRAP_TOKEN"]})
            self.assertEqual(setup.status_code,200,setup.text)
            response=await self.client.post("/auth/test-accounts",json={})
            self.assertEqual(response.status_code,200,response.text)
            result=response.json()
            self.assertEqual(len(result["accounts"]),6)
            self.assertEqual(len({a["password"] for a in result["accounts"]}),6)
            self.assertEqual((await self.client.post("/auth/test-accounts",json={})).status_code,409)
            for account in result["accounts"]:
                async with AsyncClient(transport=ASGITransport(app=app),base_url="http://test/api/v1",headers={"X-Workspace-Request":"1"}) as tester:
                    login=await tester.post("/auth/login",json={"email":account["email"],"password":account["password"]})
                    self.assertEqual(login.status_code,200,login.text)
                    self.assertEqual(login.json()["role"],account["role"])
                    plants=(await tester.get("/plants")).json()
                    self.assertEqual([p["id"] for p in plants],[result["plant_id"]])
                    self.assertEqual((await tester.get("/activities",params={"plant_id":self.plant_id})).status_code,403)
                    if account["role"] in {"director","hr"}:
                        self.assertEqual((await tester.post("/audits",json={})).status_code,403)
                        self.assertEqual((await tester.post("/activities",json={})).status_code,403)
                    if account["role"]=="zonal_leader":
                        tasks=(await tester.get("/activities")).json()
                        self.assertEqual(len(tasks),1)
                        self.assertEqual(tasks[0]["assigned_to"],login.json()["id"])
                    if account["role"]=="hr":
                        self.assertEqual((await tester.get("/management/zonal-leaders")).status_code,200)
                    self.assertEqual((await tester.post("/auth/test-accounts",json={})).status_code,403)
                    async with self.sessions() as session:
                        membership=await session.get(TestAccountMembership,login.json()["id"])
                        membership.expires_at=datetime.utcnow()-timedelta(seconds=1)
                        await session.commit()
                    self.assertEqual((await tester.get("/auth/me")).status_code,401)
                    self.assertEqual((await tester.post("/auth/login",json={"email":account["email"],"password":account["password"]})).status_code,401)
        _attempts.clear()

    async def test_comments_multiline_photos_and_internal_visibility(self):
        work=await self.create_work()
        path=f"/activities/{work['id']}"
        for bad in ["", "   ", "x"*5001]:
            self.assertEqual((await self.client.post(path+"/comments",json={"comment":bad})).status_code,422)
        saved=await self.client.post(path+"/comments",json={"comment":"  First line\nSecond line  ","attachments":[PHOTO],"author_name":"Spoofed"})
        self.assertEqual(saved.status_code,200,saved.text)
        self.assertEqual(saved.json()["author_name"],"Test Supervisor")
        self.assertEqual(saved.json()["comment"],"First line\nSecond line")
        self.assertEqual(saved.json()["attachments"],[PHOTO])
        await self.client.post(path+"/comments",json={"comment":"Reviewer-only note","is_internal":True,"attachments":[PHOTO]})
        own=(await self.client.get(path)).json()
        self.assertEqual(len(own["comments"]),2)
        self.assertTrue(any(h["action_note"]=="Comment added" for h in own["history"]))
        leader=await self.add_identity("zonal_leader","PhotoLeader",self.zone_id)
        async with self.sessions() as session:
            activity=await session.get(Activity,work["id"]);activity.assigned_to=leader;await session.commit()
        await self.client.post("/auth/local-session",json={"profile_id":leader})
        visible=(await self.client.get(path)).json()["comments"]
        self.assertEqual(len(visible),1)
        self.assertEqual(visible[0]["attachments"],[PHOTO])
        self.assertEqual((await self.client.post(path+"/comments",json={"comment":"Private","is_internal":True})).status_code,403)

    async def test_image_validation_metadata_and_evidence_locks(self):
        work=await self.create_work();path=f"/activities/{work['id']}"
        bad_images=["https://example.com/photo.png","data:image/png;base64,aGVsbG8=",PHOTO.replace("image/png","image/jpeg"),"data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=","data:image/png;base64,"+base64.b64encode(b"x"*(3*1024*1024+1)).decode()]
        for photo in bad_images:
            response=await self.client.post(path+"/report",json={"corrective_action":"Updated","after_photo_url":photo})
            self.assertEqual(response.status_code,422)
        evidence={"file_name":"forged.jpg","file_url":PHOTO,"media_type":"before_photo","mime_type":"image/jpeg","file_size_bytes":999}
        result=await self.client.post(path+"/evidence",json=evidence)
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.json()["mime_type"],"image/png")
        self.assertEqual(result.json()["file_size_bytes"],len(_photo.getvalue()))
        self.assertEqual(result.json()["uploaded_by"],self.supervisor_id)
        await self.client.post(path+"/report",json={"corrective_action":"Updated","before_photo_url":PHOTO,"after_photo_url":PHOTO})
        self.assertEqual((await self.client.post(path+"/evidence",json=evidence)).status_code,409)
        reviewer = await self.add_identity("supervisor", "EvidenceReviewer")
        await self.client.post("/auth/local-session",json={"profile_id":reviewer})
        await self.client.post(path+"/review",json={"decision":"approve"})
        self.assertEqual((await self.client.post(path+"/evidence",json=evidence)).status_code,409)
        persisted=(await self.client.get(path)).json()
        self.assertEqual(len(persisted["evidence"]),3)
        self.assertEqual(persisted["evidence"][-1]["mime_type"],"image/png")

    async def test_red_tag_photos_hold_and_closed_record_guards(self):
        payload={"plant_id":self.plant_id,"zone_id":self.zone_id,"item_name":"Unused jig","reason":"No longer used","quantity":1,"photo_url":PHOTO}
        self.assertEqual((await self.client.post("/redtags",json={**payload,"quantity":0})).status_code,422)
        self.assertEqual((await self.client.post("/redtags",json={**payload,"photo_url":"invalid"})).status_code,422)
        created=await self.client.post("/redtags",json=payload)
        self.assertEqual(created.status_code,200,created.text)
        tag=created.json();path=f"/redtags/{tag['id']}/disposition"
        self.assertEqual((await self.client.get("/redtags")).json()[0]["photo_url"],PHOTO)
        self.assertEqual((await self.client.put(path,json={"disposition":"hold_for_evaluation","disposition_notes":"Inspect later","is_closed":True})).status_code,422)
        self.assertEqual((await self.client.put(path,json={"disposition":"scrap","disposition_notes":"   ","is_closed":True})).status_code,422)
        hold=await self.client.put(path,json={"disposition":"hold_for_evaluation","disposition_notes":"Inspect later","is_closed":False})
        self.assertEqual(hold.status_code,200)
        self.assertFalse(hold.json()["is_closed"])
        close={"disposition":"relocate","disposition_notes":"Moved to the approved storage area","is_closed":True}
        self.assertEqual((await self.client.put(path,json=close)).status_code,200)
        self.assertEqual((await self.client.put(path,json=close)).status_code,409)

    async def test_audit_notes_and_photos_persist(self):
        payload={"plant_id":self.plant_id,"zone_id":self.zone_id,"zone_name":"Untrusted","sort_score":0,"set_in_order_score":80,"shine_score":90,"standardize_score":95,"sustain_score":100,"notes":"Finding one\nFinding two","photos":[PHOTO]}
        self.assertEqual((await self.client.post("/audits",json={**payload,"photos":["bad"]})).status_code,422)
        created=await self.client.post("/audits",json=payload)
        self.assertEqual(created.status_code,200,created.text)
        saved=(await self.client.get("/audits")).json()[0]
        self.assertEqual(saved["photos"],[PHOTO])
        self.assertEqual(saved["notes"],payload["notes"])
        self.assertEqual(saved["score_percentage"],73)
        self.assertEqual(saved["zone_name"],"Workbench")

    async def test_pdf_handles_markup_text_without_interpreting_it(self):
        response=await self.client.post("/activities",json={"plant_id":self.plant_id,"zone_id":self.zone_id,"title":"Inspect <b> & tools","problem_description":"Use A < B & check > C\nNext line"})
        self.assertEqual(response.status_code,200,response.text)
        pdf=await self.client.get(f"/reports/activity/{response.json()['id']}/pdf")
        self.assertEqual(pdf.status_code,200,pdf.text[:100] if pdf.status_code!=200 else "")
        self.assertTrue(pdf.content.startswith(b"%PDF"))

    async def test_browser_empty_json_start_and_malformed_body(self):
        work=await self.create_work();path=f"/activities/{work['id']}/start"
        response=await self.client.post(path,headers={"Content-Type":"application/json"})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()["status"],"in_progress")
        response=await self.client.post(path,content="not-json",headers={"Content-Type":"application/json"})
        self.assertEqual(response.status_code,422)
        self.assertEqual((await self.client.post(path,json=[])).status_code,422)

    async def test_assignee_eligibility_and_independent_report_review(self):
        director=await self.add_identity("management","ReadOnlyAssignee")
        misplaced=await self.add_identity("zonal_leader","NoAssignedZone")
        payload={"plant_id":self.plant_id,"zone_id":self.zone_id,"title":"Assignment validation","problem_description":"Assign executable work"}
        for person in [director,misplaced]:
            self.assertEqual((await self.client.post("/activities",json={**payload,"assigned_to":person})).status_code,422)
        work=await self.create_work();path=f"/activities/{work['id']}"
        self.assertEqual((await self.client.post(path+"/report",json={"corrective_action":"Completed","after_photo_url":PHOTO})).status_code,200)
        self.assertEqual((await self.client.post(path+"/review",json={"decision":"approve"})).status_code,403)
        self.assertEqual((await self.client.post(path+"/review",json={"decision":"reject","rejection_reason":"Self review"})).status_code,403)
        reviewer=await self.add_identity("supervisor","ActualReviewer")
        await self.client.post("/auth/local-session",json={"profile_id":reviewer})
        self.assertEqual((await self.client.post(path+"/review",json={"decision":"approve"})).status_code,200)

    async def test_jpeg_webp_and_png_metadata(self):
        work=await self.create_work()
        for format,mime in [("PNG","image/png"),("JPEG","image/jpeg"),("WEBP","image/webp")]:
            buffer=io.BytesIO();Image.new("RGB",(20,20),"#1d359d").save(buffer,format=format)
            photo=f"data:{mime};base64,"+base64.b64encode(buffer.getvalue()).decode()
            response=await self.client.post(f"/activities/{work['id']}/evidence",json={"file_name":"untrusted.bin","file_url":photo})
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json()["mime_type"],mime)
            self.assertEqual(response.json()["file_size_bytes"],len(buffer.getvalue()))

if __name__ == "__main__":
    unittest.main()
