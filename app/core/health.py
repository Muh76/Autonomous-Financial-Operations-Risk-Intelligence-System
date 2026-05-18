import asyncio
from collections.abc import Awaitable, Callable
from time import perf_counter

from app.core.config import settings
from app.core.graph.workflow import build_investigation_workflow
from app.schemas.common import HealthComponent, HealthStatus


async def run_health_check(
    check: Callable[[], Awaitable[bool]],
    *,
    success_detail: str,
    failure_detail: str,
) -> HealthComponent:
    started_at = perf_counter()
    try:
        healthy = await asyncio.wait_for(check(), timeout=settings.health_check_timeout_seconds)
    except TimeoutError:
        return HealthComponent(
            status="failed",
            latency_ms=_elapsed_ms(started_at),
            detail=f"{failure_detail}: timeout",
        )
    except Exception as exc:
        return HealthComponent(
            status="failed",
            latency_ms=_elapsed_ms(started_at),
            detail=f"{failure_detail}: {exc.__class__.__name__}",
        )

    return HealthComponent(
        status="ok" if healthy else "failed",
        latency_ms=_elapsed_ms(started_at),
        detail=success_detail if healthy else failure_detail,
    )


async def check_fastapi_application(ready: bool) -> bool:
    return ready


async def check_langgraph_workflow() -> bool:
    workflow = build_investigation_workflow()
    return workflow is not None


def summarize_health(components: dict[str, HealthComponent]) -> HealthStatus:
    critical_components = {"app", "langgraph"}
    if any(
        component.status == "failed"
        for name, component in components.items()
        if name in critical_components
    ):
        return "failed"
    if any(component.status == "failed" for component in components.values()):
        return "degraded"
    return "ok"


def _elapsed_ms(started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 2)
