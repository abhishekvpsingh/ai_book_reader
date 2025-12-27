import logging
from rq import Connection, Worker
from redis import Redis
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    redis_conn = Redis.from_url(settings.redis_url)
    with Connection(redis_conn):
        worker = Worker(["default"])
        logger.info("Worker starting")
        worker.work()
