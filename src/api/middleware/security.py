from __future__ import annotations

import time
from collections import defaultdict, deque
from uuid import uuid4

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.api.config import ApiSettings


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = request.headers.get("x-request-id") or uuid4().hex
        started = time.monotonic()
        response = await call_next(request)
        response.headers["x-request-id"] = request.state.request_id
        response.headers["x-process-time-ms"] = str(int((time.monotonic() - started) * 1000))
        return response


class LocalAuthMiddleware(BaseHTTPMiddleware):
    public_paths = {"/api/health", "/api/status", "/api/metrics", "/docs", "/openapi.json", "/redoc"}

    def __init__(self, app, settings: ApiSettings):
        super().__init__(app)
        self.settings = settings

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.public_paths or request.url.path.startswith("/ws/"):
            return await call_next(request)
        expected = self.settings.api_key
        provided = request.headers.get("x-api-key") or request.headers.get("authorization", "").removeprefix("Bearer ").strip()
        if expected and provided != expected:
            return JSONResponse(
                {"error": "unauthorized", "message": "API key local requerida.", "request_id": getattr(request.state, "request_id", None)},
                status_code=401,
            )
        return await call_next(request)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_bytes: int):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        length = request.headers.get("content-length")
        if length and int(length) > self.max_bytes:
            return JSONResponse({"error": "request_too_large", "message": "Request demasiado grande."}, status_code=413)
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit_per_minute: int):
        super().__init__(app)
        self.limit = limit_per_minute
        self.clients = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/api/health":
            return await call_next(request)
        now = time.monotonic()
        key = request.client.host if request.client else "local"
        bucket = self.clients[key]
        while bucket and now - bucket[0] > 60:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return JSONResponse({"error": "rate_limited", "message": "Rate limit excedido."}, status_code=429)
        bucket.append(now)
        return await call_next(request)
