import pytest

from app.core.graph.fraud_detection_node import fraud_detection_node
from app.services.fraud_detection import FraudDetectionService

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
            "device_id": "device_new",
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
            "device_id": "device_new",
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
            "device_id": "device_new",
        },
    ]


@pytest.mark.asyncio
async def test_fraud_detection_service_generates_explainable_signals() -> None:
    result = await FraudDetectionService().detect(
        transaction_id="txn_3",
        transactions=_history(),
        customer_jurisdiction="US",
        device_id="device_new",
        known_device_ids=["device_home"],
        merchant_category="crypto",
    )
    signals = set(result["signals"])

    assert result["fraud_score"] >= 90
    assert result["risk_band"] == "critical"
    assert "structuring_signal" in signals
    assert "device_mismatch" in signals
    assert "merchant_risk" in signals
    assert result["evidence"]
    assert all(item["description"] for item in result["evidence"])
    assert result["escalation_recommendation"] == "temporary_hold"


@pytest.mark.asyncio
async def test_fraud_detection_node_returns_langgraph_partial_state(low_risk_state) -> None:
    state = {
        **low_risk_state,
        "transaction_history": _history(),
        "transaction": {"device_id": "device_new"},
        "customer_profile": {"jurisdiction": "US", "known_device_ids": ["device_home"]},
        "merchant_profile": {"category": "crypto"},
    }

    result = await fraud_detection_node(state)

    assert result["status"] == "compliance_validation"
    assert result["fraud_detection"]["transaction_id"] == state["transaction_id"]
    assert result["fraud_score"] == result["fraud_detection"]["fraud_score"]
    assert result["evidence"][0]["source_system"] == "fraud_detection_agent"
    assert result["findings"][0]["source_node"] == "fraud_detection"
    assert result["agent_executions"][0]["provider"] == "hybrid_rules_ai_assisted"
