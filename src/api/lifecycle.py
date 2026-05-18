from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.dependencies import local_agent


@asynccontextmanager
async def lifespan(app: FastAPI):
    local_agent()
    yield
