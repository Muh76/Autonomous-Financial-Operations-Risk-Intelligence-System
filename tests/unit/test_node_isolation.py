import pytest

from app.core.graph.nodes import (
    collect_transaction_context_node,
    compliance_validation_node,
    escalation_router_node,
    fraud_analysis_node,
    human_approval_checkpoint_node,
    risk_scoring_node,
)
from app.core.graph.state import InvestigationState

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_collect_transaction_context_adds_evidence_and_subject(
    low_risk_state: InvestigationState,
) -> None:
    result = await collect_transaction_context_node(low_risk_state)

    assert result["status"] == "fraud_analysis"
    assert result["transaction"]["transaction_id"] == "test_txn"
    assert result["subject"]["kyc_status"] == "verified"
    assert len(result["evidence"]) == 1
    assert result["agent_executions"][0]["agent_role"] == "transaction_investigator"


@pytest.mark.asyncio
async def test_fraud_analysis_is_deterministic_for_same_amount(
    high_risk_state: InvestigationState,
) -> None:
    first = await fraud_analysis_node(high_risk_state)
    second = await fraud_analysis_node(high_risk_state)

    assert first["fraud_score"] == second["fraud_score"]
    assert first["fraud_typologies"] == second["fraud_typologies"]
    assert "high_value_anomaly" in first["fraud_typologies"]


@pytest.mark.asyncio
async def test_compliance_validation_flags_sanctioned_jurisdiction(
    sanctions_state: InvestigationState,
) -> None:
    result = await compliance_validation_node(sanctions_state)

    assert result["compliance_score"] == 95.0
    assert "sanctions_hit" in result["compliance_flags"]
    assert result["compliance_review"]["jurisdiction_checked"] is True


@pytest.mark.asyncio
async def test_risk_scoring_aggregates_fraud_and_compliance_scores(
    low_risk_state: InvestigationState,
) -> None:
    state = {
        **low_risk_state,
        "fraud_score": 30.0,
        "compliance_score": 20.0,
        "compliance_flags": [],
    }

    result = await risk_scoring_node(state)

    assert result["aggregate_risk_score"] == 25.5
    assert result["risk_band"] == "low"
    assert result["escalation_level"] == "none"
    assert result["next_route"] == "risk_router"


@pytest.mark.asyncio
async def test_escalation_router_creates_pending_approval_for_high_risk(
    high_risk_state: InvestigationState,
) -> None:
    state = {**high_risk_state, "risk_band": "high", "escalation_level": "senior_review"}

    result = await escalation_router_node(state)

    assert result["status"] == "awaiting_human_approval"
    assert result["next_route"] == "human_approval_checkpoint"
    assert result["approvals"][0]["status"] == "pending"
    assert result["escalations"][0]["approval_id"] == result["approvals"][0]["approval_id"]


@pytest.mark.asyncio
async def test_human_checkpoint_pauses_when_approval_is_pending(
    high_risk_state: InvestigationState,
) -> None:
    state = {
        **high_risk_state,
        "approvals": [
            {
                "approval_id": "approval_1",
                "checkpoint_name": "pre_final_action",
                "reason": "High risk requires review.",
                "required_role": "senior_investigator",
                "status": "pending",
            }
        ],
    }

    result = await human_approval_checkpoint_node(state)

    assert result["status"] == "awaiting_human_approval"
    assert result["workflow_history"][0]["status"] == "interrupted"
