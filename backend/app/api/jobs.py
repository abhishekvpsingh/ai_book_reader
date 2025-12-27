from fastapi import APIRouter
from rq.job import Job, NoSuchJobError
from redis import Redis
from app.core.config import settings

router = APIRouter()


@router.get("/jobs/{job_id}")
def get_job(job_id: str):
    redis_conn = Redis.from_url(settings.redis_url)
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except NoSuchJobError:
        return {"id": job_id, "status": "not_found", "result": None}
    return {"id": job.id, "status": job.get_status(), "result": job.result}
