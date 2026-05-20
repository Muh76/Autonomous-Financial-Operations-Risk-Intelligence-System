import pytest

from app.core.graph.risk_scoring_agent_node import risk_scoring_agent_node
from app.services.risk_scoring import RiskScoringService

pytestmark = pytest.mark.unit


def _state(base):
    return {
        **base,
        "fraud_score": 92.0,
        "compliance_score": 75.0,
        "compliance_flags": ["sar_threshold_met"],
        "critic_passed": False,
        "critic_notes": ["Evidence needs stronger citation support."],
        "fraud_detection": {
            "transaction_id": "txn_1",
            "fraud_score": 92.0,
            "risk_band": "critical",
            "confidence": 0.91,
            "signals": ["structuring_signal", "rapid_chain_movement"],
            "evidence": [],
            "heuristics": [],
            "geographic_inconsistencies": [],
            "suspicious_behaviors": [],
            "escalation_recommendation": "temporary_hold",
            "explanation": "Critical fraud indicators detected.",
            "recommended_actions": ["place_temporary_hold"],
        },
        "transaction_analysis": {
            "transaction_id": "txn_1",
            "aggregate": {
                "transaction_count": 3,
                "total_amount": 29_500.0,
                "average_amount": 9_833.33,
                "max_amount": 9_900.0,
                "currency": "USD",
                "unique_counterparties": 1,
                "inbound_amount": 0.0,
                "outbound_amount": 29_500.0,
            },
            "temporal": {
                "first_seen_at": "2026-05-20T01:02:00+00:00",
                "last_seen_at": "2026-05-20T01:14:00+00:00",
                "window_minutes": 12.0,
                "transactions_per_hour": 15.0,
                "burst_count": 2,
                "unusual_hour_count": 3,
            },
            "chain": [],
            "indicators": [],
            "anomaly_score": 88.0,
            "confidence": 0.82,
            "summary": "Structuring pattern detected.",
            "recommended_actions": ["senior_review"],
        },
        "financial_retrieval": {
            "query": "AML structuring escalation",
            "retrieval_intent": "risk_scoring",
            "results": [],
            "evidence": [{"evidence_id": "retrieval_ev_1"}],
            "citations": [{"citation_id": "cite_1"}],
            "confidence": 0.72,
            "answer_summary": "Grounded AML escalation evidence retrieved.",
            "source_attribution": ["AML Monitoring Guidance"],
            "recommended_actions": ["attach_citations"],
        },
        "evidence": [{"evidence_id": "ev_1"}],
    }


@pytest.mark.asyncio
async def test_risk_scoring_service_prioritizes_critical_operational_risk(low_risk_state):
    score = await RiskScoringService().score(_state(low_risk_state))

    assert score["risk_band"] == "critical"
    assert score["escalation"]["level"] == "block"
    assert score["escalation"]["priority"] == 1
    assert score["confidence"] > 0.5
    assert not score["evidence_gaps"]
    assert any(signal["signal_name"] == "fraud" for signal in score["signals"])


@pytest.mark.asyncio
async def test_risk_scoring_node_returns_langgraph_partial_state(low_risk_state):
    result = await risk_scoring_agent_node(_state(low_risk_state))

    assert result["status"] == "risk_scoring"
    assert result["next_route"] == "escalation_router"
    assert result["operational_risk"]["risk_band"] == "critical"
    assert result["risk_assessment"]["scoring_model_version"] == "weighted-operational-risk-v1"
    assert result["findings"][0]["source_node"] == "risk_scoring_agent"
    assert result["agent_executions"][0]["provider"] == "deterministic_weighted_scoring"
