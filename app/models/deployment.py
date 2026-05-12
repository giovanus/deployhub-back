from sqlalchemy import Column, Integer, Boolean, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Deployment(Base):
    __tablename__ = "deployments"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Métadonnées
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True, default=list)  # list[str]
    slug = Column(String, unique=True, index=True, nullable=False)

    # Source
    source_type = Column(String, nullable=False)  # "github" | "zip"
    source_url = Column(String, nullable=True)
    branch = Column(String, nullable=True, default="main")

    # État
    status = Column(
        String, default="pending", nullable=False
    )  # pending, cloning, extracting, building, starting, running, stopped, failed
    app_type = Column(String, nullable=True)  # web | api | cli | unknown
    error_message = Column(Text, nullable=True)

    # Docker
    container_id = Column(String, nullable=True)
    image_id = Column(String, nullable=True)
    image_tag = Column(String, nullable=True)
    port = Column(Integer, nullable=True)
    app_url = Column(String, nullable=True)
    env_vars = Column(JSON, nullable=True)
    is_compose = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_deployed_at = Column(DateTime(timezone=True), nullable=True)

    owner = relationship("User", back_populates="deployments")
    builds = relationship(
        "Build",
        back_populates="deployment",
        cascade="all, delete-orphan",
        order_by="Build.started_at.desc()",
    )

