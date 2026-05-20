from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.core.graph.retry import RetryPolicy, with_node_resilience
from app.core.graph.state import (
    AgentExecution,
    EvidenceRef,
    FraudDetectionResult,
    InvestigationFinding,
    InvestigationState,
    TransactionObservation,
    WorkflowEvent,
)
from app.services.fraud_detection import FraudDetectionService

PartialState = dict[str, Any]


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _event(message: str) -> WorkflowEvent:
    return {
        "event_id": f"evt_{uuid4().hex}",
        "node": "fraud_detection",
        "status": "completed",
        "message": message,
        "created_at": _now(),
    }


def _evidence(result: FraudDetectionResult) -> EvidenceRef:
    return {
        "evidence_id": f"ev_{uuid4().hex}",
        "evidence_type": "external_intelligence",
        "source_system": "fraud_detection_agent",
        "uri": f"evidence://fraud-detection/{uuid4().hex}",
        "collected_at": _now(),
        "summary": result["explanation"],
    }


def _finding(result: FraudDetectionResult, evidence_id: str) -> InvestigationFinding:
    return {
        "finding_id": f"finding_{uuid4().hex}",
        "category": "fraud",
        "severity": result["risk_band"],
        "description": result["explanation"],
        "evidence_ids": [evidence_id],
        "confidence": result["confidence"],
        "source_node": "fraud_detection",
    }


def _agent_execution(result: FraudDetectionResult) -> AgentExecution:
    return {
        "execution_id": f"exec_{uuid4().hex}",
        "agent_role": "fraud_analyst",
        "node": "fraud_detection",
        "provider": "hybrid_rules_ai_assisted",
        "model": "fraud-detection-ruleset-v1",
        "started_at": _now(),
        "completed_at": _now(),
        "confidence": result["confidence"],
        "status": "success",
    }


def _transactions_from_state(state: InvestigationState) -> list[TransactionObservation]:
    if state.get("transaction_history"):
        return state["transaction_history"]
    return [
        {
            "transaction_id": state["transaction_id"],
            "amount": float(state.get("transaction_amount", 0.0)),
            "currency": state.get("transaction_currency", "USD"),
            "occurred_at": state.get("transaction", {}).get("occurred_at", _now()),
            "account_id": state.get("account_ids", ["unknown_account"])[0]
            if state.get("account_ids")
            else "unknown_account",
            "counterparty_id": state.get("merchant_id", "unknown_counterparty"),
            "direction": "outbound",
            "jurisdiction": state.get("jurisdiction", "US"),
            "device_id": state.get("transaction", {}).get("device_id"),
        }
    ]


def _next_route(result: FraudDetectionResult) -> str:
    if result["risk_band"] in {"high", "critical"}:
        return "risk_scoring"
    if result["escalation_recommendation"] in {"senior_review", "temporary_hold"}:
        return "risk_scoring"
    return "compliance_validation"


async def fraud_detection_node(
    state: InvestigationState,
    *,
    service: FraudDetectionService | None = None,
) -> PartialState:
    """LangGraph-compatible node wrapper for explainable fraud detection."""

    detection_service = service or FraudDetectionService()

    async def handler(current: InvestigationState) -> PartialState:
        result = await detection_service.detect(
            transaction_id=current["transaction_id"],
            transactions=_transactions_from_state(current),
            transaction_analysis=current.get("transaction_analysis"),
            customer_jurisdiction=current.get("customer_profile", {}).get("jurisdiction")
            if current.get("customer_profile")
            else current.get("jurisdiction"),
            device_id=current.get("transaction", {}).get("device_id"),
            known_device_ids=current.get("customer_profile", {}).get("known_device_ids", [])
            if current.get("customer_profile")
            else [],
            merchant_category=current.get("merchant_profile", {}).get("category")
            if current.get("merchant_profile")
            else None,
        )
        evidence = _evidence(result)
        return {
            "status": "compliance_validation",
            "next_route": _next_route(result),
            "fraud_detection": result,
            "fraud_score": result["fraud_score"],
            "risk_band": result["risk_band"],
            "confidence": result["confidence"],
            "fraud_typologies": list(result["signals"]),
            "recommended_actions": result["recommended_actions"],
            "evidence": [evidence],
            "findings": [_finding(result, evidence["evidence_id"])],
            "agent_executions": [_agent_execution(result)],
            "workflow_history": [_event("Fraud detection completed.")],
        }

    async def fallback(current: InvestigationState) -> PartialState:
        return {
            "status": "compliance_validation",
            "next_route": "compliance_validation",
            "fraud_score": 50.0,
            "fraud_typologies": ["fraud_detection_fallback"],
            "recommended_actions": ["analyst_review"],
            "workflow_history": [_event("Fraud detection fallback used.")],
        }

    return await with_node_resilience(
        "fraud_detection",
        state,
        handler,
        fallback,
        policy=RetryPolicy(
            max_attempts=2,
            retry_route="evidence_expansion",
            fallback_name="deterministic_fallback",
        ),
    )
