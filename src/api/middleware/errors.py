from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class SafeErrorMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, dev_mode: bool = False):
        super().__init__(app)
        self.dev_mode = dev_mode

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as error:
            return JSONResponse(
                {
                    "error": "internal_error",
                    "message": str(error) if self.dev_mode else "Error interno controlado.",
                    "request_id": getattr(request.state, "request_id", None),
                },
                status_code=500,
            )
