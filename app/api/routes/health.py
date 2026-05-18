from fastapi import APIRouter

from app.api.dependencies import RequestIdDep, SettingsDep
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: SettingsDep, request_id: RequestIdDep) -> HealthResponse:
    return HealthResponse(
        status="ok",
        environment=settings.app_env,
        request_id=request_id,
    )
