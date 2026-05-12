from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.api import api_router
from app.core.config import settings
from app.core.database import Base, engine

# Import des modèles pour que SQLAlchemy enregistre les tables
from app import models  # noqa: F401

# DEV-only : si Alembic n'a pas encore tourné, on crée les tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url="/openapi.json",
)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/")
def root():
    return {"message": "Welcome to DeployHub API", "version": settings.VERSION}


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(api_router)

