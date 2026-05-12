from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Build(Base):
    """Historique des builds/déploiements d'un projet."""

    __tablename__ = "builds"

    id = Column(Integer, primary_key=True, index=True)
    deployment_id = Column(
        Integer, ForeignKey("deployments.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status = Column(String, default="pending", nullable=False)
    # pending, cloning, extracting, building, starting, running, failed, stopped
    error_message = Column(Text, nullable=True)
    logs = Column(Text, nullable=True)

    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    deployment = relationship("Deployment", back_populates="builds")
