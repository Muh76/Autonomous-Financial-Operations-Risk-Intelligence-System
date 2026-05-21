import pytest

from app.core.graph.compliance_agent_node import compliance_agent_node
from app.services.compliance import ComplianceAgentService

pytestmark = pytest.mark.unit


def _state(base):
    return {
        **base,
        "transaction_amount": 12_500.0,
        "jurisdiction": "US",
        "subject": {
            "customer_id": "cust_1",
            "account_ids": ["acct_1"],
            "kyc_status": "verified",
        },
        "fraud_detection": {"signals": ["structuring_signal", "rapid_chain_movement"]},
        "financial_retrieval": {
            "query": "AML policy structuring",
            "retrieval_intent": "compliance_validation",
            "results": [],
            "evidence": [],
            "citations": [
                {
                    "citation_id": "cite_aml_1",
                    "document_id": "aml_guidance_001",
                    "chunk_id": "chunk_1",
                    "title": "AML Monitoring Guidance",
                    "source_uri": "policy://aml/monitoring-guidance",
                    "document_type": "aml_guidance",
                    "quote": "AML programs should monitor structuring.",
                    "attribution": "AML Monitoring Guidance",
                }
            ],
            "confidence": 0.72,
            "answer_summary": "AML policy evidence retrieved.",
            "source_attribution": ["AML Monitoring Guidance"],
            "recommended_actions": ["attach_citations"],
        },
        "evidence": [{"evidence_id": "ev_policy_1"}],
    }


@pytest.mark.asyncio
async def test_compliance_service_flags_threshold_and_suspicious_activity(low_risk_state):
    result = await ComplianceAgentService().validate(_state(low_risk_state))

    assert result["passed"] is False
    assert "sar_threshold_met" in result["flags"]
    assert "suspicious_activity_review_required" in result["flags"]
    assert result["recommendation"]["level"] == "regulatory"
    assert result["citations"]


@pytest.mark.asyncio
async def test_compliance_service_blocks_sanctioned_jurisdiction(low_risk_state):
    state = {**_state(low_risk_state), "jurisdiction": "IR"}

    result = await ComplianceAgentService().validate(state)

    assert "sanctions_hit" in result["flags"]
    assert result["recommendation"]["level"] == "block"
    assert result["compliance_score"] >= 80


@pytest.mark.asyncio
async def test_compliance_node_returns_langgraph_partial_state(low_risk_state):
    result = await compliance_agent_node(_state(low_risk_state))

    assert result["status"] == "risk_scoring"
    assert result["compliance_validation"]["flags"]
    assert result["compliance_review"]["aml_rules_evaluated"] is True
    assert result["findings"][0]["source_node"] == "compliance_agent"
    assert result["agent_executions"][0]["provider"] == "deterministic_compliance_rules"
