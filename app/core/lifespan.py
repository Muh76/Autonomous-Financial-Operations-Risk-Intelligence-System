from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.cache.redis import close_redis_pool, initialize_redis_pool
from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import close_database_engine

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.app_name = settings.app_name
    initialize_redis_pool()
    app.state.ready = True
    logger.info(
        "application_startup",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
    )
    yield
    app.state.ready = False
    await close_redis_pool()
    await close_database_engine()
    logger.info(
        "application_shutdown",
        app_name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
    )
