"""Rate limiting middleware for FastAPI."""

import time
from collections import defaultdict

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.config import get_settings

settings = get_settings()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter per IP address.

    Limits requests to `max_requests` per `window_seconds` per IP.
    For production, replace with Redis-backed rate limiting.
    """

    def __init__(self, app, max_requests: int = 0, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests or settings.rate_limit_per_minute
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip rate limiting for health checks and MCP health endpoints
        if request.url.path in ("/health", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)
        if "/health" in request.url.path and request.method == "GET":
            return await call_next(request)

        # Get client identifier
        client_ip = request.client.host if request.client else "unknown"

        # Check for API key in header (higher limit for API keys)
        api_key = request.headers.get("X-API-Key")
        if api_key:
            client_ip = f"apikey:{api_key[:8]}"
            limit = self.max_requests * 10  # 10x higher limit for API key users
        else:
            limit = self.max_requests

        now = time.time()
        window_start = now - self.window_seconds

        # Clean old entries
        self._requests[client_ip] = [
            t for t in self._requests[client_ip] if t > window_start
        ]

        # Check limit
        if len(self._requests[client_ip]) >= limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Max {limit} requests per {self.window_seconds}s.",
                headers={"Retry-After": str(self.window_seconds)},
            )

        # Record this request
        self._requests[client_ip].append(now)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - len(self._requests[client_ip])))
        return response
