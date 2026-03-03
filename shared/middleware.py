"""FastAPI middleware for request tracing and correlation IDs."""
import uuid
import time
import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


class TracingMiddleware(BaseHTTPMiddleware):
    """Adds correlation IDs and request timing to all requests."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request with tracing context."""
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        start_time = time.time()

        # Bind correlation ID to log context
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            method=request.method,
            path=str(request.url.path),
        )

        logger.info("request_started")

        try:
            response = await call_next(request)
            latency_ms = (time.time() - start_time) * 1000
            logger.info(
                "request_completed",
                status_code=response.status_code,
                latency_ms=round(latency_ms, 2),
            )
            response.headers["X-Correlation-ID"] = correlation_id
            response.headers["X-Latency-Ms"] = str(round(latency_ms, 2))
            return response
        except Exception as exc:
            latency_ms = (time.time() - start_time) * 1000
            logger.error("request_failed", error=str(exc), latency_ms=round(latency_ms, 2))
            raise
