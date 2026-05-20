import pytest

from app.core.graph.transaction_analysis_node import transaction_analysis_node
from app.services.transaction_analysis import TransactionAnalysisService

pytestmark = pytest.mark.unit


def _history() -> list[dict[str, object]]:
    return [
        {
            "transaction_id": "txn_1",
            "amount": 9_750.0,
            "currency": "USD",
            "occurred_at": "2026-05-20T01:02:00+00:00",
            "account_id": "acct_123",
            "counterparty_id": "cp_shared",
            "direction": "outbound",
            "jurisdiction": "US",
        },
        {
            "transaction_id": "txn_2",
            "amount": 9_900.0,
            "currency": "USD",
            "occurred_at": "2026-05-20T01:08:00+00:00",
            "account_id": "acct_123",
            "counterparty_id": "cp_shared",
            "direction": "outbound",
            "jurisdiction": "US",
        },
        {
            "transaction_id": "txn_3",
            "amount": 9_850.0,
            "currency": "USD",
            "occurred_at": "2026-05-20T01:14:00+00:00",
            "account_id": "acct_123",
            "counterparty_id": "cp_shared",
            "direction": "outbound",
            "jurisdiction": "GB",
        },
    ]


@pytest.mark.asyncio
async def test_transaction_analysis_service_detects_structuring_and_chain_depth() -> None:
    result = await TransactionAnalysisService().analyze(
        transaction_id="txn_3",
        transactions=_history(),
    )
    indicators = {item["indicator"] for item in result["indicators"]}

    assert result["aggregate"]["transaction_count"] == 3
    assert result["aggregate"]["unique_counterparties"] == 1
    assert "structuring" in indicators
    assert "rapid_movement" in indicators
    assert "chain_depth" in indicators
    assert result["anomaly_score"] >= 80
    assert result["confidence"] > 0.6


@pytest.mark.asyncio
async def test_transaction_analysis_node_returns_langgraph_partial_state(
    low_risk_state,
) -> None:
    state = {**low_risk_state, "transaction_history": _history()}

    result = await transaction_analysis_node(state)

    assert result["status"] == "fraud_analysis"
    assert result["transaction_analysis"]["transaction_id"] == state["transaction_id"]
    assert result["fraud_score"] == result["transaction_analysis"]["anomaly_score"]
    assert result["evidence"][0]["source_system"] == "transaction_analysis_agent"
    assert result["findings"][0]["source_node"] == "transaction_analysis"
    assert result["agent_executions"][0]["model"] == "transaction-analysis-ruleset-v1"
