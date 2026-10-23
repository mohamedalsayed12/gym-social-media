import logging
import time
import uuid
from contextvars import ContextVar

from fastapi import Request

request_id: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id.get()
        return True


def setup_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s")
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)


access_log = logging.getLogger("app.access")


async def request_context(request: Request, call_next):
    """Tag every log line and response with a request id, so one request can be traced across
    workers. A load balancer's X-Request-ID is reused when present."""
    token = request_id.set(request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16])
    started = time.perf_counter()
    try:
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started) * 1000
        access_log.info("%s %s %s %.1fms", request.method, request.url.path, response.status_code, elapsed_ms)
        response.headers["X-Request-ID"] = request_id.get()
        return response
    finally:
        request_id.reset(token)
