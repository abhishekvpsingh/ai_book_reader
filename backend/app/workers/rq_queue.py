from redis import Redis
from rq import Queue
from app.core.config import settings


def get_queue() -> Queue:
    redis_conn = Redis.from_url(settings.redis_url)
    return Queue("default", connection=redis_conn, default_timeout=settings.rq_default_timeout)
