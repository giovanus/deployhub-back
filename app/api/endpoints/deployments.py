import json
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app import crud, schemas
from app.core.database import get_db
from app.core.deps import get_current_active_user
from app.models.user import User
from app.schemas.deployment import (
    DeploymentCreateGithub,
    DeploymentResponse,
    DeploymentStats,
    DeploymentUpdate,
)
from app.services.deployment_service import DeploymentService, save_upload
from app.tasks.deployment_tasks import execute_deployment_task

router = APIRouter()


def _get_owned_deployment(deployment_id: int, db: Session, current_user: User):
    deployment = crud.deployment.get_for_user(
        db, deployment_id=deployment_id, user_id=current_user.id
    )
    if not deployment:
        raise HTTPException(status_code=404, detail="Deployment not found")
    return deployment


# -------- READ --------

@router.get("/", response_model=List[DeploymentResponse])
def list_deployments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    status: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    return crud.deployment.list_for_user(
        db, user_id=current_user.id, status=status, tag=tag, search=search
    )


@router.get("/stats", response_model=DeploymentStats)
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return crud.deployment.stats_for_user(db, user_id=current_user.id)


@router.get("/{deployment_id}", response_model=DeploymentResponse)
def get_deployment(
    deployment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return _get_owned_deployment(deployment_id, db, current_user)


@router.get("/{deployment_id}/builds", response_model=List[schemas.BuildSummary])
def get_builds(
    deployment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    deployment = _get_owned_deployment(deployment_id, db, current_user)
    return crud.deployment.list_builds(db, deployment_id=deployment.id)


@router.get("/{deployment_id}/logs", response_model=dict)
def get_logs(
    deployment_id: int,
    tail: int = 500,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    deployment = _get_owned_deployment(deployment_id, db, current_user)
    service = DeploymentService(db)
    return {"logs": service.get_container_logs(deployment, tail=tail)}


# -------- CREATE --------

@router.post("/github", response_model=DeploymentResponse, status_code=202)
def deploy_github(
    data: DeploymentCreateGithub,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    deployment = crud.deployment.create_github(db, user_id=current_user.id, obj_in=data)
    execute_deployment_task.delay(deployment.id)
    return deployment


@router.post("/zip", response_model=DeploymentResponse, status_code=202)
def deploy_zip(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # JSON list or comma-separated
    env_vars: Optional[str] = Form(None),  # JSON dict
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not file.filename or not file.filename.lower().endswith((".zip",)):
        raise HTTPException(status_code=400, detail="Only .zip files are allowed")

    parsed_tags: Optional[List[str]] = None
    if tags:
        try:
            parsed_tags = json.loads(tags)
            if not isinstance(parsed_tags, list):
                raise ValueError
        except (ValueError, json.JSONDecodeError):
            parsed_tags = [t.strip() for t in tags.split(",") if t.strip()]

    parsed_env: Optional[dict] = None
    if env_vars:
        try:
            parsed_env = json.loads(env_vars)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="env_vars must be valid JSON")

    zip_path = save_upload(file.file, suffix=".zip")

    deployment = crud.deployment.create_zip(
        db,
        user_id=current_user.id,
        name=name,
        description=description,
        tags=parsed_tags,
        zip_path=zip_path,
        env_vars=parsed_env,
    )
    execute_deployment_task.delay(deployment.id)
    return deployment


# -------- UPDATE / DELETE --------

@router.patch("/{deployment_id}", response_model=DeploymentResponse)
def update_deployment(
    deployment_id: int,
    payload: DeploymentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    deployment = _get_owned_deployment(deployment_id, db, current_user)
    return crud.deployment.update(db, deployment=deployment, obj_in=payload)


@router.delete("/{deployment_id}", status_code=204)
def delete_deployment(
    deployment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    deployment = _get_owned_deployment(deployment_id, db, current_user)
    service = DeploymentService(db)
    service.remove(deployment)
    return None


# -------- ACTIONS --------

@router.post("/{deployment_id}/stop", response_model=DeploymentResponse)
def stop_deployment(
    deployment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    deployment = _get_owned_deployment(deployment_id, db, current_user)
    return DeploymentService(db).stop(deployment)


@router.post("/{deployment_id}/restart", response_model=DeploymentResponse)
def restart_deployment(
    deployment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    deployment = _get_owned_deployment(deployment_id, db, current_user)
    try:
        return DeploymentService(db).restart(deployment)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{deployment_id}/rebuild", response_model=DeploymentResponse, status_code=202)
def rebuild_deployment(
    deployment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    deployment = _get_owned_deployment(deployment_id, db, current_user)
    # On nettoie le container existant et on relance le pipeline
    service = DeploymentService(db)
    container = service._get_container(deployment) if service.docker_client else None
    if container:
        try:
            container.remove(force=True)
        except Exception:
            pass
    deployment.container_id = None
    crud.deployment.set_status(db, deployment=deployment, status="pending", error_message=None)
    execute_deployment_task.delay(deployment.id)
    return deployment


@router.post("/{deployment_id}/duplicate", response_model=DeploymentResponse, status_code=201)
def duplicate_deployment(
    deployment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    src = _get_owned_deployment(deployment_id, db, current_user)
    if src.source_type != "github":
        raise HTTPException(
            status_code=400, detail="Only GitHub-based projects can be duplicated"
        )
    new_data = DeploymentCreateGithub(
        name=f"{src.name} (copy)",
        description=src.description,
        tags=src.tags,
        github_url=src.source_url,
        branch=src.branch or "main",
        env_vars=src.env_vars,
    )
    deployment = crud.deployment.create_github(db, user_id=current_user.id, obj_in=new_data)
    execute_deployment_task.delay(deployment.id)
    return deployment

