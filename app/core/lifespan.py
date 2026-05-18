from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.core.config import settings

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.app_name = settings.app_name
    logger.info("application_startup", app_name=settings.app_name, environment=settings.app_env)
    yield
    logger.info("application_shutdown", app_name=settings.app_name, environment=settings.app_env)
