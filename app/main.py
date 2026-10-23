import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

import app.models  # noqa: F401
from app.core.config import settings
from app.core.logging import request_context, setup_logging
from app.core.rate_limit import limiter
from app.routers import auth, communities, feed, users, workouts
from app.services.storage import LocalStorage, get_storage

API_PREFIX = "/api/v1"

setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(title="Gym Social", openapi_url=f"{API_PREFIX}/openapi.json", docs_url=f"{API_PREFIX}/docs")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.middleware("http")(request_context)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)
for router in (auth.router, users.router, workouts.router, feed.router, communities.router):
    app.include_router(router, prefix=API_PREFIX)

storage = get_storage()
if isinstance(storage, LocalStorage):
    app.mount("/media", StaticFiles(directory=storage.directory), name="media")


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request, exc: Exception):
    logger.exception("Unhandled error", exc_info=exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health")
def health():
    return {"status": "ok"}
