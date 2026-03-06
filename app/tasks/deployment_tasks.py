import asyncio
from app.core.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.deployment_service import DeploymentService
from app.models.deployment import Deployment
import logging

logger = logging.getLogger(__name__)

@celery_app.task(name="app.tasks.deployment_tasks.execute_deployment_task")
def execute_deployment_task(deployment_id: int):
    db = SessionLocal()
    try:
        service = DeploymentService(db)
        # Using asyncio.run to execute the async service method in the sync celery worker
        asyncio.run(service.execute_deployment(deployment_id))
    except Exception as e:
        logger.error(f"Deployment {deployment_id} failed: {str(e)}")
        # The service already handles status="failed", but we log it here
    finally:
        db.close()
