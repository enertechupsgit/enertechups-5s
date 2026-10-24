from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.plants import router as plants_router
from app.api.activities import router as activities_router
from app.api.red_tags import router as red_tags_router
from app.api.audits import router as audits_router
from app.api.reports import router as reports_router
from app.api.management import router as management_router
from app.seed import seed_data
from app.api.assets import router as assets_router
import os
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from app.core.access import enforce_access
from app.api.auth import router as auth_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto-initialize and seed database on startup
    try:
        if os.getenv("APP_ENV") == "production":
            if not settings.DATABASE_URL.startswith(("postgres://", "postgresql://", "postgresql+asyncpg://")):
                raise RuntimeError("Production requires persistent PostgreSQL DATABASE_URL")
            if os.getenv("LOCAL_DEMO") == "1":
                raise RuntimeError("Local sample switching cannot be enabled in production")
            if not os.getenv("BOOTSTRAP_TOKEN"):
                raise RuntimeError("Configure BOOTSTRAP_TOKEN for protected administrator setup")
        await seed_data()
        if os.getenv("LOCAL_DEMO") == "1":
            from app.sample_data import seed_sample_workspace
            await seed_sample_workspace()
            from app.sample_data import ensure_sample_identities
            await ensure_sample_identities()
    except Exception as e:
        raise RuntimeError("Workspace database initialization failed") from e
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Enterprise 5S Activity Management, Before/After Evidence Tracking & Plant Zone Auditing API",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
for protected_router in [plants_router, activities_router, red_tags_router, audits_router, reports_router, management_router, assets_router]:
    app.include_router(protected_router, prefix=settings.API_V1_PREFIX, dependencies=[Depends(enforce_access)])
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)

@app.get("/")
async def root():
    frontend = Path(os.getenv("FRONTEND_DIST", ""))
    if (frontend / "index.html").is_file():
        return FileResponse(frontend / "index.html", headers={"Cache-Control": "no-cache"})
    return {
        "platform": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "operational",
        "docs_url": "/docs"
    }

@app.get("/health")
async def health_check():
    async with AsyncSessionLocal() as db:
        await db.execute(text("SELECT 1"))
    return {"status": "healthy", "workspace": "sample" if os.getenv("LOCAL_DEMO") == "1" else "live", "authentication": "session", "local_role_switch": os.getenv("LOCAL_DEMO") == "1"}

frontend = Path(os.getenv("FRONTEND_DIST", ""))
for folder in ("assets", "brand"):
    if (frontend / folder).is_dir():
        app.mount(f"/{folder}", StaticFiles(directory=frontend / folder), name=f"frontend-{folder}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
