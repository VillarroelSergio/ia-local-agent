from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.config import get_api_settings
from src.api.lifecycle import lifespan
from src.api.middleware.errors import SafeErrorMiddleware
from src.api.middleware.security import LocalAuthMiddleware, RateLimitMiddleware, RequestContextMiddleware, RequestSizeLimitMiddleware
from src.api.routes import chat, computer_use, conversations, health, memory, settings as settings_routes, system, tools, workflows
from src.api.ws import chat as ws_chat
from src.api.ws import events as ws_events


def create_app() -> FastAPI:
    settings = get_api_settings()
    app = FastAPI(
        title="IA Local Agent API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.expose_docs else None,
        redoc_url="/redoc" if settings.expose_docs else None,
    )
    app.add_middleware(SafeErrorMiddleware, dev_mode=settings.dev_mode)
    app.add_middleware(RateLimitMiddleware, limit_per_minute=settings.rate_limit_per_minute)
    app.add_middleware(RequestSizeLimitMiddleware, max_bytes=settings.request_size_limit)
    app.add_middleware(LocalAuthMiddleware, settings=settings)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.allowed_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "PATCH"],
        allow_headers=["x-api-key", "authorization", "content-type", "x-request-id"],
    )
    app.include_router(health.router, prefix="/api", tags=["health"])
    app.include_router(chat.router, prefix="/api", tags=["chat"])
    app.include_router(tools.router, prefix="/api", tags=["tools"])
    app.include_router(memory.router, prefix="/api", tags=["memory"])
    app.include_router(conversations.router, prefix="/api", tags=["conversations"])
    app.include_router(workflows.router, prefix="/api", tags=["workflows"])
    app.include_router(computer_use.router, prefix="/api", tags=["computer_use"])
    app.include_router(settings_routes.router, prefix="/api", tags=["settings"])
    app.include_router(system.router, prefix="/api", tags=["system"])
    app.include_router(ws_chat.router)
    app.include_router(ws_events.router)
    return app


app = create_app()
