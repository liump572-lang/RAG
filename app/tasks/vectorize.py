from app.tasks.celery_app import celery_app


@celery_app.task(name="vectorize_chunk", bind=True, max_retries=3)
def vectorize_chunk(self, chunk_id: int, content: str):
    return {"status": "success", "chunk_id": chunk_id}
