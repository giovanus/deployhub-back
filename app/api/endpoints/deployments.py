import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
import json

from app.core.database import get_db
from app.schemas.deployment import DeploymentCreateGithub, DeploymentResponse
from app.services.deployment_service import DeploymentService

router = APIRouter()

@router.post("/github", response_model=DeploymentResponse)
async def deploy_github(
    data: DeploymentCreateGithub,
    db: Session = Depends(get_db)
):
    service = DeploymentService(db)
    try:
        deployment = await service.deploy_from_github(data)
        return deployment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")

@router.post("/zip", response_model=DeploymentResponse)
async def deploy_zip(
    name: str = Form(...),
    env_vars: Optional[str] = Form(None),  # JSON string
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip files are allowed")

    # Parse env_vars if provided
    parsed_env = None
    if env_vars:
        try:
            parsed_env = json.loads(env_vars)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="env_vars must be a valid JSON string")

    # Save to temp file
    temp_zip = f"/tmp/{file.filename}"
    with open(temp_zip, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    service = DeploymentService(db)
    try:
        deployment = await service.deploy_from_zip(name, temp_zip, parsed_env)
        return deployment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")
    finally:
        if os.path.exists(temp_zip):
            os.remove(temp_zip)
