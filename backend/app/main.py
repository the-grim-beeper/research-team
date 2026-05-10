from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.db import SessionLocal
from app.services.users import ensure_admin_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with SessionLocal() as session:
        await ensure_admin_user(session, settings.admin_email, settings.admin_password)
    yield


app = FastAPI(title="Research Team", version="0.1.0", lifespan=lifespan)


@app.get("/api/v1/health")
async def health() -> dict:
    return {"status": "ok"}
