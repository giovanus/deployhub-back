import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
import json

from app.core.database import get_db
from app.schemas.deployment import DeploymentCreateGithub, DeploymentResponse
from app.services.deployment_service import DeploymentService
from app.models.deployment import Deployment
from app.tasks.deployment_tasks import execute_deployment_task

router = APIRouter()

@router.post("/github", response_model=DeploymentResponse, status_code=202)
async def deploy_github(
    data: DeploymentCreateGithub,
    db: Session = Depends(get_db)
):
    service = DeploymentService(db)
    try:
        # 1. Create record
        deployment = await service.start_github_deployment(data)
        
        # 2. Trigger background task
        execute_deployment_task.delay(deployment.id)
        
        return deployment
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start deployment: {str(e)}")

@router.post("/zip", response_model=DeploymentResponse, status_code=202)
async def deploy_zip(
    name: str = Form(...),
    env_vars: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are allowed")

    parsed_env = None
    if env_vars:
        try:
            parsed_env = json.loads(env_vars)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="env_vars must be a valid JSON string")

    # Save to a persistent location for the worker (e.g., /tmp with a unique name)
    # Note: In a production environment, this should be uploaded to a shared storage (S3/Minio) 
    # since workers might be on different machines.
    temp_zip = f"/tmp/deploy_{file.filename}"
    with open(temp_zip, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    service = DeploymentService(db)
    try:
        # 1. Create record
        deployment = await service.start_zip_deployment(name, temp_zip, parsed_env)
        
        # 2. Trigger background task
        execute_deployment_task.delay(deployment.id)
        
        return deployment
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start deployment: {str(e)}")

@router.get("/{deployment_id}", response_model=DeploymentResponse)
async def get_deployment(
    deployment_id: int,
    db: Session = Depends(get_db)
):
    deployment = db.query(Deployment).filter(Deployment.id == deployment_id).first()
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return deployment

@router.get("/", response_model=List[DeploymentResponse])
async def list_deployments(
    db: Session = Depends(get_db)
):
    return db.query(Deployment).all()
