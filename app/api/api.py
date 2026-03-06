from fastapi import APIRouter
from app.api.endpoints import auth, deployments

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(deployments.router, prefix="/deployments", tags=["deployments"])
