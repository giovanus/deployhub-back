from fastapi import FastAPI
from app.api.api import api_router
from app.core.config import settings
from app.core.database import engine
from app.models.user import User
from app.models.deployment import Deployment

# Create database tables
from app.core.database import Base
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url="/openapi.json"
)

@app.get("/")
async def root():
    return {"message": "Welcome to DeployHub API"}

app.include_router(api_router)
