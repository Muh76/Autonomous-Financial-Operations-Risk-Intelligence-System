import pytest

from app.core.graph.reporting_agent_node import reporting_agent_node
from app.services.reporting import ExecutiveReportingService

pytestmark = pytest.mark.unit


def _state(base):
    return {
        **base,
        "risk_band": "critical",
        "escalation_level": "block",
        "financial_retrieval": {
            "query": "AML escalation evidence",
            "retrieval_intent": "reporting",
            "results": [],
            "evidence": [],
            "citations": [
                {
                    "citation_id": "cite_1",
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
            "answer_summary": "AML evidence retrieved.",
            "source_attribution": ["AML Monitoring Guidance"],
            "recommended_actions": ["attach_citations"],
        },
        "fraud_detection": {
            "risk_band": "critical",
            "confidence": 0.91,
            "explanation": "Critical fraud indicators detected.",
        },
        "operational_risk": {
            "severity_score": 94.0,
            "risk_band": "critical",
            "confidence": 0.88,
            "explanation": "Operational risk is critical.",
            "escalation": {
                "level": "block",
                "rationale": "Critical risk requires controlled escalation.",
            },
            "recommended_actions": ["place_temporary_hold", "senior_review"],
        },
        "critic_validation": {
            "passed": True,
            "reliability_score": 0.9,
            "confidence": 0.84,
            "summary": "Critic validation passed.",
            "safety_recommendation": "continue",
            "required_actions": ["continue_workflow"],
        },
        "evidence": [{"evidence_id": "ev_1"}],
    }


@pytest.mark.asyncio
async def test_reporting_service_generates_citation_backed_report(low_risk_state):
    report = await ExecutiveReportingService().generate(_state(low_risk_state))

    assert report["status"] == "ready_for_review"
    assert report["confidence"] >= 0.65
    assert report["citations"]
    assert report["findings"]
    assert "critical" in report["executive_summary"]


@pytest.mark.asyncio
async def test_reporting_node_returns_report_draft_and_uri(low_risk_state):
    result = await reporting_agent_node(_state(low_risk_state))

    assert result["status"] == "closed"
    assert result["executive_report"]["citations"]
    assert result["report_draft"].startswith("# Executive Investigation Report")
    assert result["final_report_uri"].startswith("reports://investigations/")
    assert result["agent_executions"][0]["provider"] == "deterministic_reporting_service"
