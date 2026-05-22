import pytest

from app.core.graph.critic_agent_node import critic_agent_node
from app.services.critic import CriticService

pytestmark = pytest.mark.unit


def _valid_state(base):
    return {
        **base,
        "risk_band": "critical",
        "compliance_flags": ["sar_threshold_met"],
        "fraud_detection": {
            "transaction_id": "txn_1",
            "fraud_score": 91.0,
            "risk_band": "critical",
            "confidence": 0.88,
            "signals": ["structuring_signal"],
            "evidence": [],
            "heuristics": [],
            "geographic_inconsistencies": [],
            "suspicious_behaviors": ["Structuring detected."],
            "escalation_recommendation": "temporary_hold",
            "explanation": "Critical fraud indicators detected.",
            "recommended_actions": ["place_temporary_hold"],
        },
        "financial_retrieval": {
            "query": "AML structuring escalation",
            "retrieval_intent": "critic_validation",
            "results": [],
            "evidence": [{"evidence_id": "retrieval_ev_1"}],
            "citations": [{"citation_id": "cite_1"}],
            "confidence": 0.74,
            "answer_summary": "Grounded AML escalation evidence retrieved.",
            "source_attribution": ["AML Monitoring Guidance"],
            "recommended_actions": ["attach_citations"],
        },
        "operational_risk": {
            "aggregate_score": 72.0,
            "severity_score": 94.0,
            "risk_band": "critical",
            "confidence": 0.8,
            "signals": [{"signal_name": "fraud"}, {"signal_name": "compliance"}],
            "escalation": {
                "level": "block",
                "priority": 1,
                "required_role": "compliance_officer",
                "rationale": "Critical risk requires controlled escalation.",
                "recommended_actions": ["place_temporary_hold"],
            },
            "critic_adjustments": [],
            "evidence_gaps": [],
            "recommended_actions": ["place_temporary_hold"],
            "explanation": "Critical operational risk.",
            "policy_version": "operational-risk-policy-v1",
            "scoring_model_version": "weighted-operational-risk-v1",
        },
        "compliance_validation": {
            "passed": False,
            "score": 68.0,
            "flags": ["sar_threshold_met"],
            "rule_results": [],
            "citations": [{"citation_id": "cite_1"}],
            "recommendation": {
                "level": "regulatory",
                "rationale": "SAR threshold requires review.",
                "required_actions": ["prepare_sar_review"],
            },
            "suspicious_activity_summary": "Structuring review required.",
            "policy_version": "aml-compliance-policy-v1",
            "confidence": 0.74,
        },
        "evidence": [{"evidence_id": "ev_1"}],
    }


@pytest.mark.asyncio
async def test_critic_service_passes_grounded_consistent_outputs(low_risk_state):
    result = await CriticService().validate(_valid_state(low_risk_state))

    assert result["passed"] is True
    assert result["reliability_score"] >= 0.72
    assert result["safety_recommendation"] == "continue"
    assert not result["contradictions"]
    assert result["score_breakdown"]["citation_support_score"] == 1.0
    assert result["citation_validation"]
    assert result["retrieval_grounding"]
    assert result["reasoning_consistency"]


@pytest.mark.asyncio
async def test_critic_service_detects_contradiction_and_missing_citation(low_risk_state):
    state = _valid_state(low_risk_state)
    state.pop("financial_retrieval")
    state["operational_risk"]["risk_band"] = "low"

    result = await CriticService().validate(state)

    assert result["passed"] is False
    assert result["safety_recommendation"] in {"human_review", "block_final_action"}
    assert result["contradictions"]
    assert any(finding["finding_type"] == "missing_citation" for finding in result["findings"])


@pytest.mark.asyncio
async def test_critic_service_detects_invalid_reporting_citation(low_risk_state):
    state = _valid_state(low_risk_state)
    state["executive_report"] = {
        "report_id": "report_1",
        "case_id": state["case_id"],
        "transaction_id": state["transaction_id"],
        "audience": "executive",
        "title": "Investigation Report",
        "executive_summary": "Critical fraud indicators require escalation.",
        "investigation_summary": "Investigation summary.",
        "risk_summary": "Risk summary.",
        "escalation_summary": "Escalation summary.",
        "audit_explanation": "Audit explanation.",
        "evidence_summary": "Evidence summary.",
        "findings": [
            {
                "finding_id": "finding_1",
                "severity": "critical",
                "title": "Critical risk",
                "summary": "Critical risk requires escalation.",
                "evidence_ids": ["ev_1"],
                "citation_ids": ["missing_cite"],
                "confidence": 0.9,
            }
        ],
        "sections": [],
        "citations": [
            {
                "citation_id": "generated_cite",
                "title": "Generated citation",
                "source_uri": "memory://generated",
                "attribution": "Generated",
                "quote": "Generated citation text.",
            }
        ],
        "confidence": 0.92,
        "status": "ready_for_review",
        "recommended_actions": ["escalate"],
        "generated_at": "2026-05-21T00:00:00Z",
    }

    result = await CriticService().validate(state)

    assert result["passed"] is False
    assert any(finding["finding_type"] == "invalid_citation" for finding in result["findings"])
    assert result["citation_validation"][2]["invalid_citations"] == 1
    assert result["citation_validation"][2]["missing_citations"] == 1


@pytest.mark.asyncio
async def test_critic_node_returns_langgraph_partial_state(low_risk_state):
    result = await critic_agent_node(_valid_state(low_risk_state))

    assert result["status"] == "critic_validation"
    assert result["critic_validation"]["passed"] is True
    assert result["critic_passed"] is True
    assert result["next_route"] == "report_generation"
    assert result["findings"][0]["source_node"] == "critic_agent"
    assert result["agent_executions"][0]["provider"] == "deterministic_reliability_validator"
