import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.db import SessionLocal
from app.routes import agents as agent_routes
from app.routes import artifacts as artifact_routes
from app.routes import auth as auth_routes
from app.routes import execution as execution_routes
from app.routes import library as library_routes
from app.routes import roles as role_routes
from app.routes import standup as standup_routes
from app.routes import subjects as subject_routes
from app.services import scheduler
from app.services.users import ensure_admin_user

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    stream=sys.stdout,
    force=True,
)
log = logging.getLogger("app.lifespan")

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "out"


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("lifespan: bootstrapping admin user")
    async with SessionLocal() as session:
        await ensure_admin_user(session, settings.admin_email, settings.admin_password)
    log.info("lifespan: starting scheduler")
    await scheduler.start(SessionLocal)
    log.info("lifespan: ready")
    try:
        yield
    finally:
        log.info("lifespan: shutting down scheduler")
        await scheduler.shutdown()


app = FastAPI(title="Research Team", version="0.1.0", lifespan=lifespan)
app.include_router(auth_routes.router)
app.include_router(subject_routes.router)
app.include_router(role_routes.router)
app.include_router(agent_routes.router)
app.include_router(artifact_routes.router)
app.include_router(execution_routes.router)
app.include_router(library_routes.router)
app.include_router(standup_routes.router)


@app.get("/api/v1/health")
async def health() -> dict:
    return {"status": "ok"}


if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
