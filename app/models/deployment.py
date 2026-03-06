from sqlalchemy import Column, Integer,Boolean, String, DateTime, JSON
from sqlalchemy.sql import func
from app.core.database import Base

class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    source_type = Column(String, nullable=False)  # "github" or "zip"
    source_url = Column(String, nullable=True)
    status = Column(String, default="pending")  # pending, building, running, failed, stopped
    container_id = Column(String, nullable=True)
    image_id = Column(String, nullable=True)
    port = Column(Integer, nullable=True)
    app_url = Column(String, nullable=True)
    env_vars = Column(JSON, nullable=True)
    is_compose = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
