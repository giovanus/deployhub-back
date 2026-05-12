import secrets
from datetime import datetime
from typing import Optional, List

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.deployment import Deployment
from app.models.build import Build
from app.schemas.deployment import (
    DeploymentCreateGithub,
    DeploymentUpdate,
)


def _generate_slug(name: str) -> str:
    base = "".join(c.lower() if c.isalnum() else "-" for c in name).strip("-")[:40] or "project"
    suffix = secrets.token_hex(3)
    return f"{base}-{suffix}"


# ------- READ -------

def get(db: Session, *, deployment_id: int) -> Optional[Deployment]:
    return db.query(Deployment).filter(Deployment.id == deployment_id).first()


def get_for_user(db: Session, *, deployment_id: int, user_id: int) -> Optional[Deployment]:
    return (
        db.query(Deployment)
        .filter(Deployment.id == deployment_id, Deployment.user_id == user_id)
        .first()
    )


def list_for_user(
    db: Session,
    *,
    user_id: int,
    status: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
) -> List[Deployment]:
    query = db.query(Deployment).filter(Deployment.user_id == user_id)
    if status:
        query = query.filter(Deployment.status == status)
    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(Deployment.name.ilike(like), Deployment.description.ilike(like))
        )
    deployments = query.order_by(Deployment.created_at.desc()).all()
    if tag:
        deployments = [d for d in deployments if d.tags and tag in d.tags]
    return deployments


def stats_for_user(db: Session, *, user_id: int) -> dict:
    items = db.query(Deployment).filter(Deployment.user_id == user_id).all()
    return {
        "total": len(items),
        "running": sum(1 for d in items if d.status == "running"),
        "stopped": sum(1 for d in items if d.status == "stopped"),
        "building": sum(1 for d in items if d.status in ("pending", "cloning", "extracting", "building", "starting")),
        "failed": sum(1 for d in items if d.status == "failed"),
    }


# ------- CREATE -------

def create_github(db: Session, *, user_id: int, obj_in: DeploymentCreateGithub) -> Deployment:
    deployment = Deployment(
        user_id=user_id,
        name=obj_in.name,
        description=obj_in.description,
        tags=obj_in.tags or [],
        slug=_generate_slug(obj_in.name),
        source_type="github",
        source_url=obj_in.github_url,
        branch=obj_in.branch or "main",
        status="pending",
        env_vars=obj_in.env_vars,
    )
    db.add(deployment)
    db.commit()
    db.refresh(deployment)
    return deployment


def create_zip(
    db: Session,
    *,
    user_id: int,
    name: str,
    description: Optional[str],
    tags: Optional[List[str]],
    zip_path: str,
    env_vars: Optional[dict],
) -> Deployment:
    deployment = Deployment(
        user_id=user_id,
        name=name,
        description=description,
        tags=tags or [],
        slug=_generate_slug(name),
        source_type="zip",
        source_url=zip_path,
        status="pending",
        env_vars=env_vars,
    )
    db.add(deployment)
    db.commit()
    db.refresh(deployment)
    return deployment


# ------- UPDATE / DELETE -------

def update(db: Session, *, deployment: Deployment, obj_in: DeploymentUpdate) -> Deployment:
    data = obj_in.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(deployment, field, value)
    db.commit()
    db.refresh(deployment)
    return deployment


def set_status(
    db: Session,
    *,
    deployment: Deployment,
    status: str,
    error_message: Optional[str] = None,
) -> Deployment:
    deployment.status = status
    if error_message is not None:
        deployment.error_message = error_message
    if status == "running":
        deployment.last_deployed_at = datetime.utcnow()
    db.commit()
    db.refresh(deployment)
    return deployment


def remove(db: Session, *, deployment: Deployment) -> None:
    db.delete(deployment)
    db.commit()


# ------- BUILDS -------

def create_build(db: Session, *, deployment_id: int) -> Build:
    build = Build(deployment_id=deployment_id, status="pending")
    db.add(build)
    db.commit()
    db.refresh(build)
    return build


def list_builds(db: Session, *, deployment_id: int) -> List[Build]:
    return (
        db.query(Build)
        .filter(Build.deployment_id == deployment_id)
        .order_by(Build.started_at.desc())
        .all()
    )


def finalize_build(
    db: Session,
    *,
    build: Build,
    status: str,
    error_message: Optional[str] = None,
    logs: Optional[str] = None,
) -> Build:
    build.status = status
    build.error_message = error_message
    if logs is not None:
        build.logs = logs
    build.finished_at = datetime.utcnow()
    db.commit()
    db.refresh(build)
    return build
