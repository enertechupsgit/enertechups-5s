"""Explicit local-preview fixtures. Never invoked unless LOCAL_DEMO=1."""
from datetime import datetime, timedelta
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.models import Plant, Department, Zone, Profile, Activity, ActivityHistory, AuditRun, RedTag, Asset, AssetStatusEvent

async def seed_sample_workspace():
    async with AsyncSessionLocal() as db:
        if (await db.execute(select(Department))).scalars().first():
            return
        plant = (await db.execute(select(Plant))).scalars().first()
        if not plant:
            return
        now = datetime.utcnow()
        departments = [Department(plant_id=plant.id, name=name, code=code) for name, code in [("Production & Assembly", "PROD"), ("Quality & Testing", "QA"), ("Stores & Logistics", "STORES")]]
        db.add_all(departments)
        await db.flush()
        names = [("UPS Assembly Line A", "AS-01", 0), ("PCB Assembly", "PCB-01", 0), ("Final Assembly", "FA-01", 0), ("Testing & Validation", "QA-01", 1), ("Incoming Quality", "IQ-01", 1), ("Component Stores", "ST-01", 2)]
        zones = [Zone(dept_id=departments[d].id, name=name, code=code, target_score=90, current_score=0) for name, code, d in names]
        db.add_all(zones)
        await db.flush()
        people = []
        for i, (first, last) in enumerate([("Aditi", "Sharma"), ("Rahul", "Patil"), ("Neha", "Kulkarni"), ("Sanjay", "Deshmukh"), ("Priya", "Nair"), ("Amit", "Joshi")]):
            person = Profile(first_name=first, last_name=last, email=f"{first.lower()}@sample.example", role="zonal_leader", plant_id=plant.id, assigned_zone_id=zones[i].id, assigned_zone_name=zones[i].name)
            db.add(person)
            people.append(person)
        await db.flush()
        for i, zone in enumerate(zones):
            zone.leader_id = people[i].id
            zone.leader_name = f"{people[i].first_name} {people[i].last_name}"
            for week in range(4):
                values = [min(100, 70 + week * 5 + (i * 3 + s * 2) % 13) for s in range(5)]
                score = round(sum(values) / 5, 1)
                db.add(AuditRun(plant_id=plant.id, zone_id=zone.id, zone_name=zone.name, auditor_name="Sample quality auditor", sort_score=values[0], set_in_order_score=values[1], shine_score=values[2], standardize_score=values[3], sustain_score=values[4], score_percentage=score, total_score=sum(values), max_score=500, notes="Sample baseline assessment for the local preview.", conducted_at=now - timedelta(days=24 - week * 7, hours=i)))
                if week == 3:
                    zone.current_score = score
        titles = ["Label component bins at assembly station", "Create a shadow board for hand tools", "Clear the marked emergency access route", "Standardize workbench reference photographs", "Review ESD cleaning checklist", "Relocate obsolete packaging material", "Mark designated trolley parking positions", "Update visual instructions at test station", "Organize cable storage by specification", "Verify daily cleaning ownership", "Replace worn floor-identification labels", "Complete weekly 5S sustain review"]
        categories = ["sort_seiri", "set_in_order_seiton", "shine_seiso", "standardize_seiketsu", "sustain_shitsuke"]
        statuses = ["in_progress", "submitted_for_review", "assigned", "completed", "submitted_for_review", "in_progress", "assigned", "completed", "rejected", "completed", "assigned", "draft"]
        for i, title in enumerate(titles):
            zone = zones[i % len(zones)]
            work = Activity(activity_number=f"5S-{now.year}-{i + 1:04d}", plant_id=plant.id, zone_id=zone.id, category=categories[i % 5], title=title, problem_description=f"Sample observation: the current arrangement in {zone.name} needs a clearer visual standard and an accountable follow-up.", assigned_to=people[i % 6].id, priority=["medium", "high", "critical", "low"][i % 4], status=statuses[i], due_date=now + timedelta(days=(i % 7) - 2), created_at=now - timedelta(days=12-i), corrective_action="A visual standard has been prepared and reviewed with the zone team." if statuses[i] in ["completed", "submitted_for_review"] else None, reviewed_at=now - timedelta(days=2) if statuses[i] == "completed" else None, benefits_space_sqft=0, benefits_cost_savings=0, benefits_time_seconds=0)
            db.add(work)
            await db.flush()
            db.add(ActivityHistory(activity_id=work.id, actor_name="Sample workspace", to_status=work.status, action_note="Sample work order created for local evaluation.", created_at=work.created_at))
        for i, item in enumerate(["Unused cable reels", "Damaged storage trolley", "Obsolete test fixture", "Excess packaging trays"]):
            db.add(RedTag(tag_number=f"RT-{now.year}-{i + 1:04d}", plant_id=plant.id, zone_id=zones[i].id, item_name=item, reason="Sample item identified during a workplace organization round.", item_category="Equipment/Tool", quantity=i + 1, disposition="pending", is_closed=False, logged_by_name=zones[i].leader_name, created_at=now-timedelta(days=i+2)))
        for i, (name, code, manufacturer, model) in enumerate([("UPS Assembly Workbench", "ET-001", "Enertech", "Assembly 01"), ("PCB Reflow Station", "ET-002", "Production Equipment", "RF-200"), ("Battery Load Test Bench", "ET-003", "Enertech", "LT-500"), ("Industrial Air Compressor", "ET-004", "Plant Equipment", "AC-100"), ("ESD Component Cabinet", "ET-005", "Stores Equipment", "ESD-40")]):
            asset = Asset(plant_id=plant.id, zone_id=zones[i].id, name=name, code=code, manufacturer=manufacturer, model=model, description="Sample equipment registration for the local development workspace.", status="maintenance" if i == 2 else "online")
            db.add(asset)
            await db.flush()
            db.add(AssetStatusEvent(asset_id=asset.id, status=asset.status, note="Sample asset registered", created_at=now-timedelta(days=8)))
        await db.commit()


async def ensure_sample_identities():
    async with AsyncSessionLocal() as db:
        plant = (await db.execute(select(Plant))).scalars().first()
        if not plant:
            return
        for first, last, role in [("Executive", "Director", "management"), ("Plant", "Supervisor", "supervisor"), ("Quality", "Auditor", "auditor")]:
            email = f"{role}@sample.example"
            if not (await db.execute(select(Profile).where(Profile.email == email))).scalar_one_or_none():
                db.add(Profile(first_name=first, last_name=last, role=role, email=email, plant_id=plant.id))
        await db.commit()
