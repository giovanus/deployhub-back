from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from datetime import datetime


# ------- Base / Inputs -------

class DeploymentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class DeploymentCreateGithub(DeploymentBase):
    github_url: str
    branch: Optional[str] = "main"
    env_vars: Optional[Dict[str, str]] = None


class DeploymentCreateZip(DeploymentBase):
    env_vars: Optional[Dict[str, str]] = None


class DeploymentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


# ------- Outputs -------

class DeploymentResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    slug: str

    source_type: str
    source_url: Optional[str] = None
    branch: Optional[str] = None

    status: str
    app_type: Optional[str] = None
    error_message: Optional[str] = None

    container_id: Optional[str] = None
    image_id: Optional[str] = None
    image_tag: Optional[str] = None
    port: Optional[int] = None
    app_url: Optional[str] = None
    env_vars: Optional[Dict[str, str]] = None
    is_compose: bool = False

    created_at: datetime
    updated_at: Optional[datetime] = None
    last_deployed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DeploymentStats(BaseModel):
    total: int
    running: int
    stopped: int
    building: int
    failed: int

