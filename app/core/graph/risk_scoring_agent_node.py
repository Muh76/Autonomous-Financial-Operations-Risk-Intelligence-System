from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.core.graph.retry import RetryPolicy, with_node_resilience
from app.core.graph.state import (
    AgentExecution,
    InvestigationFinding,
    InvestigationState,
    OperationalRiskScore,
    WorkflowEvent,
)
from app.services.risk_scoring import RiskScoringService

PartialState = dict[str, Any]


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _event(message: str) -> WorkflowEvent:
    return {
        "event_id": f"evt_{uuid4().hex}",
        "node": "risk_scoring_agent",
        "status": "completed",
        "message": message,
        "created_at": _now(),
    }


def _finding(score: OperationalRiskScore, evidence_ids: list[str]) -> InvestigationFinding:
    return {
        "finding_id": f"finding_{uuid4().hex}",
        "category": "risk",
        "severity": score["risk_band"],
        "description": score["explanation"],
        "evidence_ids": evidence_ids,
        "confidence": score["confidence"],
        "source_node": "risk_scoring_agent",
    }


def _agent_execution(score: OperationalRiskScore) -> AgentExecution:
    return {
        "execution_id": f"exec_{uuid4().hex}",
        "agent_role": "risk_scorer",
        "node": "risk_scoring_agent",
        "provider": "deterministic_weighted_scoring",
        "model": score["scoring_model_version"],
        "started_at": _now(),
        "completed_at": _now(),
        "confidence": score["confidence"],
        "status": "success",
    }


def _next_route(score: OperationalRiskScore) -> str:
    if score["escalation"]["level"] in {"senior_review", "regulatory", "block"}:
        return "escalation_router"
    if score["risk_band"] == "medium":
        return "medium_risk_compliance_review"
    return "risk_router"


async def risk_scoring_agent_node(
    state: InvestigationState,
    *,
    service: RiskScoringService | None = None,
) -> PartialState:
    """LangGraph-compatible node wrapper for explainable operational risk scoring."""

    scoring_service = service or RiskScoringService()

    async def handler(current: InvestigationState) -> PartialState:
        score = await scoring_service.score(current)
        evidence_ids = [item["evidence_id"] for item in current.get("evidence", [])]
        return {
            "status": "risk_scoring",
            "next_route": _next_route(score),
            "operational_risk": score,
            "aggregate_risk_score": score["aggregate_score"],
            "risk_band": score["risk_band"],
            "escalation_level": score["escalation"]["level"],
            "confidence": score["confidence"],
            "recommended_actions": score["recommended_actions"],
            "risk_assessment": {
                "fraud_score": next(
                    item["raw_score"] for item in score["signals"] if item["signal_name"] == "fraud"
                ),
                "compliance_score": next(
                    item["raw_score"]
                    for item in score["signals"]
                    if item["signal_name"] == "compliance"
                ),
                "transaction_score": next(
                    item["raw_score"]
                    for item in score["signals"]
                    if item["signal_name"] == "anomaly"
                ),
                "customer_score": 0.0,
                "aggregate_score": score["aggregate_score"],
                "risk_band": score["risk_band"],
                "escalation_level": score["escalation"]["level"],
                "scoring_model_version": score["scoring_model_version"],
                "policy_version": score["policy_version"],
                "confidence": score["confidence"],
                "recommended_actions": score["recommended_actions"],
                "score_components": {
                    item["signal_name"]: item["weighted_score"] for item in score["signals"]
                },
                "explanation": score["explanation"],
            },
            "findings": [_finding(score, evidence_ids)],
            "agent_executions": [_agent_execution(score)],
            "workflow_history": [_event("Operational risk scoring completed.")],
        }

    async def fallback(current: InvestigationState) -> PartialState:
        return {
            "status": "risk_scoring",
            "next_route": "risk_router",
            "aggregate_risk_score": 50.0,
            "risk_band": "medium",
            "escalation_level": "analyst_review",
            "confidence": 0.45,
            "recommended_actions": ["analyst_review"],
            "workflow_history": [_event("Risk scoring fallback used.")],
        }

    return await with_node_resilience(
        "risk_scoring_agent",
        state,
        handler,
        fallback,
        policy=RetryPolicy(
            max_attempts=2,
            retry_route="evidence_expansion",
            fallback_name="deterministic_fallback",
        ),
    )
