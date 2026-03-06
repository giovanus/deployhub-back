from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any
from datetime import datetime

class DeploymentBase(BaseModel):
    name: str

class DeploymentCreateGithub(DeploymentBase):
    github_url: str
    branch: Optional[str] = "main"
    env_vars: Optional[Dict[str, str]] = None

class DeploymentCreateZip(DeploymentBase):
    env_vars: Optional[Dict[str, str]] = None

class DeploymentResponse(DeploymentBase):
    id: int
    source_type: str
    source_url: Optional[str] = None
    status: str
    container_id: Optional[str] = None
    image_id: Optional[str] = None
    port: Optional[int] = None
    app_url: Optional[str] = None
    env_vars: Optional[Dict[str, Any]] = None
    is_compose: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
