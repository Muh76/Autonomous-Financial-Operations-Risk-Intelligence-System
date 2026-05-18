from fastapi import APIRouter

from app.api.routes import health
from app.api.v1.router import router as api_v1_router
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(api_v1_router, prefix=settings.api_v1_prefix)
