from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.core.graph.retry import RetryPolicy, with_node_resilience
from app.core.graph.state import (
    AgentExecution,
    CriticValidationResult,
    InvestigationFinding,
    InvestigationState,
    WorkflowEvent,
)
from app.services.critic import CriticService

PartialState = dict[str, Any]


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _event(message: str, *, status: str = "completed") -> WorkflowEvent:
    return {
        "event_id": f"evt_{uuid4().hex}",
        "node": "critic_agent",
        "status": status,
        "message": message,
        "created_at": _now(),
    }


def _finding(result: CriticValidationResult) -> InvestigationFinding:
    severity = "low"
    if any(finding["severity"] in {"high", "critical"} for finding in result["findings"]):
        severity = "high"
    elif result["findings"]:
        severity = "medium"
    evidence_ids = sorted(
        {
            evidence_id
            for finding in result["findings"]
            for evidence_id in finding["evidence_refs"]
        }
    )
    return {
        "finding_id": f"finding_{uuid4().hex}",
        "category": "critic",
        "severity": severity,
        "description": result["summary"],
        "evidence_ids": evidence_ids,
        "confidence": result["confidence"],
        "source_node": "critic_agent",
    }


def _agent_execution(result: CriticValidationResult) -> AgentExecution:
    return {
        "execution_id": f"exec_{uuid4().hex}",
        "agent_role": "critic",
        "node": "critic_agent",
        "provider": "deterministic_reliability_validator",
        "model": result["model_version"],
        "started_at": _now(),
        "completed_at": _now(),
        "confidence": result["confidence"],
        "status": "success",
    }


def _next_route(result: CriticValidationResult) -> str:
    if result["safety_recommendation"] in {"expand_evidence", "revise_outputs"}:
        return "evidence_expansion"
    if result["safety_recommendation"] in {"human_review", "block_final_action"}:
        return "escalation_router"
    return "report_generation"


async def critic_agent_node(
    state: InvestigationState,
    *,
    service: CriticService | None = None,
) -> PartialState:
    """LangGraph-compatible Critic Agent for enterprise reliability validation."""

    critic_service = service or CriticService()

    async def handler(current: InvestigationState) -> PartialState:
        result = await critic_service.validate(current)
        return {
            "status": "critic_validation",
            "next_route": _next_route(result),
            "critic_validation": result,
            "critic_passed": result["passed"],
            "critic_notes": [finding["claim"] for finding in result["findings"]],
            "confidence_assessment": {
                "overall": result["reliability_score"],
                "evidence_quality": min(
                    1.0,
                    sum(
                        item["grounding_score"] for item in result["evidence_verification"]
                    )
                    / max(len(result["evidence_verification"]), 1),
                ),
                "reasoning_quality": 1.0 if not result["contradictions"] else 0.45,
                "policy_alignment": 0.9 if result["passed"] else 0.55,
                "explanation": result["summary"],
            },
            "findings": [_finding(result)],
            "agent_executions": [_agent_execution(result)],
            "workflow_history": [_event(result["summary"])],
        }

    async def fallback(current: InvestigationState) -> PartialState:
        return {
            "status": "critic_validation",
            "next_route": "human_approval_checkpoint",
            "critic_passed": False,
            "critic_notes": ["Critic fallback requires human review."],
            "workflow_history": [_event("Critic fallback used.", status="fallback")],
        }

    return await with_node_resilience(
        "critic_agent",
        state,
        handler,
        fallback,
        policy=RetryPolicy(
            max_attempts=2,
            retry_route="evidence_expansion",
            fallback_name="manual_review",
        ),
    )
