import logging
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging, request_id_ctx_var, ensure_request_id

configure_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_rate_limit_store: dict[str, list[float]] = {}


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = ensure_request_id(request.headers.get("X-Request-ID"))
    request_id_ctx_var.set(request_id)
    if settings.environment.lower() != "prod":
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = 60
    history = [t for t in _rate_limit_store.get(client_ip, []) if now - t < window]
    if len(history) >= settings.rate_limit_per_min:
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    history.append(now)
    _rate_limit_store[client_ip] = history
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(api_router)
