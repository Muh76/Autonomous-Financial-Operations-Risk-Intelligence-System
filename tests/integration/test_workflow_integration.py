import pytest

from app.core.graph.parallel_workflow import run_parallel_investigation_workflow
from app.core.graph.workflow import run_investigation_workflow

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_low_risk_workflow_closes_deterministically() -> None:
    result = await run_investigation_workflow(
        "low_risk_txn",
        tenant_id="test",
        transaction_amount=125.0,
        jurisdiction="US",
    )

    assert result["status"] == "closed"
    assert result["risk_band"] == "low"
    assert result["escalation_level"] == "none"
    assert result["final_report_uri"].endswith("/final")


@pytest.mark.asyncio
async def test_high_risk_workflow_pauses_for_human_approval() -> None:
    result = await run_investigation_workflow(
        "high_risk_txn",
        tenant_id="test",
        transaction_amount=75_000.0,
        jurisdiction="US",
    )

    assert result["status"] == "awaiting_human_approval"
    assert result["escalation_level"] in {"senior_review", "regulatory", "block"}
    assert any(approval["status"] == "pending" for approval in result["approvals"])


@pytest.mark.asyncio
async def test_parallel_workflow_aggregates_branch_results() -> None:
    result = await run_parallel_investigation_workflow(
        "parallel_txn",
        tenant_id="test",
        transaction_amount=12_500.0,
        jurisdiction="US",
    )

    assert result["status"] == "closed"
    assert result["fraud_score"] > 0
    assert result["compliance_score"] > 0
    assert result["aggregate_risk_score"] > 0
    assert result["risk_assessment"]["scoring_model_version"] == "parallel-risk-scoring-v1"
