from celery import Celery
import os

celery_app = Celery(
    "deployhub",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
)

celery_app.conf.task_routes = {
    "app.tasks.deployment_tasks.*": {"queue": "deployments"},
}

celery_app.autodiscover_tasks(["app.tasks"])
