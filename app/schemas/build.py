from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class BuildBase(BaseModel):
    status: str
    error_message: Optional[str] = None


class BuildResponse(BuildBase):
    id: int
    deployment_id: int
    started_at: datetime
    finished_at: Optional[datetime] = None
    logs: Optional[str] = None

    class Config:
        from_attributes = True


class BuildSummary(BaseModel):
    id: int
    status: str
    started_at: datetime
    finished_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True
