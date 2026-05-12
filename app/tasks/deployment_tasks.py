import logging

from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.deployment_service import DeploymentService

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.deployment_tasks.execute_deployment_task")
def execute_deployment_task(deployment_id: int):
    db = SessionLocal()
    try:
        service = DeploymentService(db)
        service.execute_deployment(deployment_id)
    except Exception as exc:
        logger.error("Deployment %s failed: %s", deployment_id, exc)
    finally:
        db.close()

