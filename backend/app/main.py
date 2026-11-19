from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    auth, health, profile, tags, mentor_directory,
    requests, mentoring,
)
from app.core.config import get_settings
from app.core.seed import seed_demo_users
from app.database import Base, SessionLocal, engine
from app import models  # noqa: F401 - ensures every model is registered before create_all

settings = get_settings()

Base.metadata.create_all(bind=engine)

with SessionLocal() as _db:
    seed_demo_users(_db)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(profile.router, prefix=settings.api_prefix)
app.include_router(profile.mentor_router, prefix=settings.api_prefix)
app.include_router(profile.student_router, prefix=settings.api_prefix)
app.include_router(tags.router, prefix=settings.api_prefix)
app.include_router(mentor_directory.router, prefix=settings.api_prefix)
app.include_router(requests.router, prefix=settings.api_prefix)
app.include_router(mentoring.router, prefix=settings.api_prefix)
