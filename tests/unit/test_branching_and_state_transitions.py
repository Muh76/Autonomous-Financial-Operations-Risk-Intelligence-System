import pytest

from app.core.graph.nodes import risk_router_node
from app.core.graph.state import InvestigationState
from app.core.graph.workflow import (
    route_after_compliance,
    route_after_context,
    route_after_critic,
    route_after_escalation,
    route_after_fraud,
    route_after_risk_router,
    route_after_risk_scoring,
)

pytestmark = pytest.mark.unit


def test_route_helpers_respect_explicit_next_route(low_risk_state: InvestigationState) -> None:
    state = {**low_risk_state, "next_route": "evidence_expansion"}

    assert route_after_context(state) == "evidence_expansion"
    assert route_after_fraud(state) == "evidence_expansion"
    assert route_after_compliance(state) == "evidence_expansion"
    assert route_after_risk_scoring(state) == "evidence_expansion"
    assert route_after_risk_router(state) == "evidence_expansion"
    assert route_after_escalation(state) == "evidence_expansion"
    assert route_after_critic(state) == "evidence_expansion"


@pytest.mark.asyncio
async def test_risk_router_sends_low_risk_to_auto_close(
    low_risk_state: InvestigationState,
) -> None:
    result = await risk_router_node(
        {**low_risk_state, "risk_band": "low", "escalation_level": "none"}
    )

    assert result["status"] == "reporting"
    assert result["next_route"] == "low_risk_auto_close"


@pytest.mark.asyncio
async def test_risk_router_sends_medium_risk_to_compliance_review(
    low_risk_state: InvestigationState,
) -> None:
    result = await risk_router_node(
        {**low_risk_state, "risk_band": "medium", "escalation_level": "analyst_review"}
    )

    assert result["status"] == "compliance_validation"
    assert result["next_route"] == "medium_risk_compliance_review"


@pytest.mark.asyncio
async def test_risk_router_sends_high_risk_to_escalation(
    high_risk_state: InvestigationState,
) -> None:
    result = await risk_router_node(
        {**high_risk_state, "risk_band": "high", "escalation_level": "senior_review"}
    )

    assert result["status"] == "awaiting_human_approval"
    assert result["next_route"] == "escalation_router"
