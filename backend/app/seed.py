import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal, engine, Base
from app.models.models import (
    Organization, Plant, Profile, UserRole
)

async def seed_data():
    async with engine.begin() as conn:
        # Ensure tables exist
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        res = await session.execute(select(Organization))
        if res.scalars().first():
            return

        print("Initializing clean enterprise baseline for Enertech 5S...")

        # 1. Organization
        org = Organization(name="EnerTech UPS Pvt. Ltd.", slug="enertech-ups")
        session.add(org)
        await session.flush()

        # 2. Plant
        plant = Plant(
            org_id=org.id,
            name="EnerTech UPS - Unit 1",
            code="ET-01",
            location="Enertech Industrial Complex",
            is_active=True
        )
        session.add(plant)
        await session.flush()

        # 3. Base User Accounts
        supervisor = Profile(
            email="vishal@enertechups.com",
            first_name="Vishal",
            last_name="Sir",
            role=UserRole.SUPERVISOR.value,
            plant_id=plant.id,
            phone_number="+91 (Operations)",
            avatar_url="https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150"
        )
        admin = Profile(
            email="management@enertechups.com",
            first_name="Enertech",
            last_name="Management",
            role=UserRole.MANAGEMENT.value,
            plant_id=plant.id,
            phone_number="+91 (HQ)",
            avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150"
        )
        session.add_all([supervisor, admin])
        await session.commit()
        print("Enertech clean initialization complete. Sections, workstations, and work orders will be defined by user.")

if __name__ == "__main__":
    asyncio.run(seed_data())
