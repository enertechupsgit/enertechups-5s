"""Public endpoint checks use an isolated DB and no plant fixtures."""
import unittest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.main import app
from app.core.database import Base, get_db

class PublicApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine=create_async_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions=async_sessionmaker(self.engine,expire_on_commit=False)
        async def dependency():
            async with self.sessions() as session:
                yield session
        app.dependency_overrides[get_db]=dependency
        self.health_patch=patch("app.main.AsyncSessionLocal",self.sessions)
        self.health_patch.start()
        self.client=AsyncClient(transport=ASGITransport(app=app),base_url="http://test")
    async def asyncTearDown(self):
        await self.client.aclose()
        app.dependency_overrides.clear()
        self.health_patch.stop()
        await self.engine.dispose()
    async def test_database_health_and_head(self):
        response=await self.client.get("/health")
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()["status"],"healthy")
        self.assertEqual((await self.client.head("/")).status_code,200)
    async def test_private_endpoints_require_sign_in(self):
        for path in ["/plants","/activities","/audits","/redtags","/assets","/management/zonal-leaders"]:
            self.assertEqual((await self.client.get("/api/v1"+path)).status_code,401)
