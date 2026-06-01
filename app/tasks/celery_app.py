from celery import Celery
from app.config import settings

celery_app = Celery(
    "knowledge_qa",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.document_parse", "app.tasks.kg_extract"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_queues={
        "parse_queue": {"exchange": "parse_queue", "routing_key": "parse_queue"},
    },
    task_routes={
        "kb_task.*": {"queue": "parse_queue"},
        "kg_task.*": {"queue": "parse_queue"},
    },
)
