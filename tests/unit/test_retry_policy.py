import pytest

from app.core.graph.retry import (
    RecoverableNodeError,
    RetryManager,
    RetryPolicy,
    with_node_resilience,
)
from app.core.graph.state import InvestigationState

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_retry_manager_routes_recoverable_failure(
    low_risk_state: InvestigationState,
) -> None:
    async def failing_handler(state: InvestigationState) -> dict[str, object]:
        raise RecoverableNodeError("temporary semantic failure")

    result = await with_node_resilience(
        "fraud_analysis",
        low_risk_state,
        failing_handler,
        policy=RetryPolicy(max_attempts=2, retry_route="evidence_expansion"),
    )

    assert result["status"] == "evidence_expansion"
    assert result["next_route"] == "evidence_expansion"
    assert result["retry_state"]["fraud_analysis"]["retryable"] is True
    assert result["node_results"][0]["status"] == "retrying"


@pytest.mark.asyncio
async def test_retry_manager_uses_fallback_after_exhaustion(
    low_risk_state: InvestigationState,
) -> None:
    async def failing_handler(state: InvestigationState) -> dict[str, object]:
        raise RecoverableNodeError("still failing")

    async def fallback_handler(state: InvestigationState) -> dict[str, object]:
        return {"fraud_score": 50.0}

    exhausted_state = {
        **low_risk_state,
        "retry_counts": {"fraud_analysis": 1},
    }

    result = await with_node_resilience(
        "fraud_analysis",
        exhausted_state,
        failing_handler,
        fallback_handler,
        policy=RetryPolicy(max_attempts=2, fallback_name="deterministic_fallback"),
    )

    assert result["fraud_score"] == 50.0
    assert result["fallback_used"]["fraud_analysis"] == "deterministic_fallback"
    assert result["retry_state"]["fraud_analysis"]["exhausted"] is True
    assert result["node_results"][0]["status"] == "fallback"


def test_error_classifier_marks_permission_as_non_recoverable() -> None:
    manager = RetryManager()
    failure_class = manager.classifier.classify(PermissionError("forbidden"))

    assert failure_class == "permission"
    assert manager.is_recoverable(failure_class, attempt=1) is False
