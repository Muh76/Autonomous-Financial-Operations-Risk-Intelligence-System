from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.core.graph.retry import RetryPolicy, with_node_resilience
from app.core.graph.state import (
    AgentExecution,
    ComplianceValidationResult,
    InvestigationFinding,
    InvestigationState,
    WorkflowEvent,
)
from app.services.compliance import ComplianceAgentService

PartialState = dict[str, Any]


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _event(message: str) -> WorkflowEvent:
    return {
        "event_id": f"evt_{uuid4().hex}",
        "node": "compliance_agent",
        "status": "completed",
        "message": message,
        "created_at": _now(),
    }


def _finding(result: ComplianceValidationResult) -> InvestigationFinding:
    severity = "low"
    if any(
        rule["severity"] == "critical" and not rule["passed"]
        for rule in result["rule_results"]
    ):
        severity = "critical"
    elif any(
        rule["severity"] == "high" and not rule["passed"]
        for rule in result["rule_results"]
    ):
        severity = "high"
    elif result["flags"]:
        severity = "medium"
    evidence_ids = sorted(
        {
            evidence_id
            for rule in result["rule_results"]
            for evidence_id in rule["evidence_refs"]
        }
    )
    return {
        "finding_id": f"finding_{uuid4().hex}",
        "category": "compliance",
        "severity": severity,
        "description": result["reasoning"],
        "evidence_ids": evidence_ids,
        "confidence": result["confidence"],
        "source_node": "compliance_agent",
    }


def _agent_execution(result: ComplianceValidationResult) -> AgentExecution:
    return {
        "execution_id": f"exec_{uuid4().hex}",
        "agent_role": "compliance_reviewer",
        "node": "compliance_agent",
        "provider": "deterministic_compliance_rules",
        "model": result["policy_version"],
        "started_at": _now(),
        "completed_at": _now(),
        "confidence": result["confidence"],
        "status": "success",
    }


def _next_route(result: ComplianceValidationResult) -> str:
    if result["recommendation"]["level"] in {"block", "regulatory"}:
        return "risk_scoring"
    if result["recommendation"]["level"] in {"compliance_review", "analyst_review"}:
        return "risk_scoring"
    return "risk_scoring"


async def compliance_agent_node(
    state: InvestigationState,
    *,
    service: ComplianceAgentService | None = None,
) -> PartialState:
    """LangGraph-compatible node wrapper for rule-based compliance validation."""

    compliance_service = service or ComplianceAgentService()

    async def handler(current: InvestigationState) -> PartialState:
        result = await compliance_service.validate(current)
        return {
            "status": "risk_scoring",
            "next_route": _next_route(result),
            "compliance_validation": result,
            "compliance_score": result["compliance_score"],
            "compliance_flags": result["flags"],
            "compliance_review": {
                "sanctions_screened": True,
                "pep_screened": True,
                "aml_rules_evaluated": True,
                "jurisdiction_checked": True,
                "flags": result["flags"],
                "policy_version": result["policy_version"],
                "reviewer_notes": [result["reasoning"]],
            },
            "recommended_actions": result["recommendation"]["recommended_actions"],
            "findings": [_finding(result)],
            "agent_executions": [_agent_execution(result)],
            "workflow_history": [_event("Compliance validation completed.")],
        }

    async def fallback(current: InvestigationState) -> PartialState:
        return {
            "status": "risk_scoring",
            "next_route": "risk_scoring",
            "compliance_score": 60.0,
            "compliance_flags": ["manual_compliance_review_required"],
            "recommended_actions": ["compliance_analyst_review"],
            "workflow_history": [_event("Compliance fallback used.")],
        }

    return await with_node_resilience(
        "compliance_agent",
        state,
        handler,
        fallback,
        policy=RetryPolicy(
            max_attempts=2,
            retry_route="evidence_expansion",
            fallback_name="manual_review",
        ),
    )
