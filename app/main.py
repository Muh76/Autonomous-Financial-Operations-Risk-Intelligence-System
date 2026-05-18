from fastapi import FastAPI

from app.api.router import api_router
from app.api.errors import register_exception_handlers
from app.core.config import settings
from app.core.lifespan import lifespan
from app.core.logging import configure_logging
from app.core.middleware import register_middleware


def create_app() -> FastAPI:
    configure_logging()

    application = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.is_local else None,
        redoc_url="/redoc" if settings.is_local else None,
    )
    register_middleware(application)
    register_exception_handlers(application)
    application.include_router(api_router)
    return application


app = create_app()
