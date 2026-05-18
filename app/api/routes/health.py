import asyncio

from fastapi import APIRouter, Request, Response, status

from app.api.dependencies import RequestIdDep, SettingsDep
from app.cache.redis import check_redis_connection
from app.core.health import (
    check_fastapi_application,
    check_langgraph_workflow,
    run_health_check,
    summarize_health,
)
from app.db.session import check_database_connection
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check(
    request: Request,
    response: Response,
    settings: SettingsDep,
    request_id: RequestIdDep,
) -> HealthResponse:
    app_ready = bool(getattr(request.app.state, "ready", False))
    app_check, database_check, redis_check, workflow_check = await asyncio.gather(
        run_health_check(
            lambda: check_fastapi_application(app_ready),
            success_detail="FastAPI application is ready",
            failure_detail="FastAPI application is not ready",
        ),
        run_health_check(
            check_database_connection,
            success_detail="PostgreSQL connectivity check passed",
            failure_detail="PostgreSQL connectivity check failed",
        ),
        run_health_check(
            check_redis_connection,
            success_detail="Redis connectivity check passed",
            failure_detail="Redis connectivity check failed",
        ),
        run_health_check(
            check_langgraph_workflow,
            success_detail="LangGraph investigation workflow compiled",
            failure_detail="LangGraph investigation workflow initialization failed",
        ),
    )
    components = {
        "app": app_check,
        "postgresql": database_check,
        "redis": redis_check,
        "langgraph": workflow_check,
    }
    overall_status = summarize_health(components)
    if overall_status == "failed":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return HealthResponse(
        status=overall_status,
        environment=settings.app_env,
        version=settings.app_version,
        components=components,
        request_id=request_id,
    )
