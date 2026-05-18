from fastapi import APIRouter

from app.api.dependencies import RequestIdDep, SettingsDep
from app.cache.redis import check_redis_connection
from app.db.session import check_database_connection
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: SettingsDep, request_id: RequestIdDep) -> HealthResponse:
    database_ok = await check_database_connection()
    redis_ok = await check_redis_connection()
    healthy = database_ok and redis_ok
    return HealthResponse(
        status="ok" if healthy else "degraded",
        environment=settings.app_env,
        database="ok" if database_ok else "unavailable",
        redis="ok" if redis_ok else "unavailable",
        request_id=request_id,
    )
