from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.core.graph.retry import RetryPolicy, with_node_resilience
from app.core.graph.state import (
    AgentExecution,
    EvidenceRef,
    InvestigationFinding,
    InvestigationState,
    RiskBand,
    TransactionObservation,
    WorkflowEvent,
)
from app.services.transaction_analysis import TransactionAnalysisService

PartialState = dict[str, Any]


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _risk_band(score: float) -> RiskBand:
    if score >= 90:
        return "critical"
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _event(message: str) -> WorkflowEvent:
    return {
        "event_id": f"evt_{uuid4().hex}",
        "node": "transaction_analysis",
        "status": "completed",
        "message": message,
        "created_at": _now(),
    }


def _evidence(summary: str) -> EvidenceRef:
    return {
        "evidence_id": f"ev_{uuid4().hex}",
        "evidence_type": "transaction_snapshot",
        "source_system": "transaction_analysis_agent",
        "uri": f"evidence://transaction-analysis/{uuid4().hex}",
        "collected_at": _now(),
        "summary": summary,
    }


def _finding(
    *,
    severity: RiskBand,
    description: str,
    evidence_id: str,
    confidence: float,
) -> InvestigationFinding:
    return {
        "finding_id": f"finding_{uuid4().hex}",
        "category": "transaction",
        "severity": severity,
        "description": description,
        "evidence_ids": [evidence_id],
        "confidence": confidence,
        "source_node": "transaction_analysis",
    }


def _agent_execution(confidence: float) -> AgentExecution:
    return {
        "execution_id": f"exec_{uuid4().hex}",
        "agent_role": "transaction_investigator",
        "node": "transaction_analysis",
        "provider": "deterministic_service",
        "model": "transaction-analysis-ruleset-v1",
        "started_at": _now(),
        "completed_at": _now(),
        "confidence": confidence,
        "status": "success",
    }


def _transactions_from_state(state: InvestigationState) -> list[TransactionObservation]:
    if state.get("transaction_history"):
        return state["transaction_history"]

    occurred_at = state.get("transaction", {}).get("occurred_at", _now())
    return [
        {
            "transaction_id": state["transaction_id"],
            "amount": float(state.get("transaction_amount", 0.0)),
            "currency": state.get("transaction_currency", "USD"),
            "occurred_at": occurred_at,
            "account_id": state.get("account_ids", ["unknown_account"])[0]
            if state.get("account_ids")
            else "unknown_account",
            "counterparty_id": state.get("merchant_id", "unknown_counterparty"),
            "direction": "outbound",
            "jurisdiction": state.get("jurisdiction", "US"),
            "channel": state.get("transaction", {}).get("channel"),
            "device_id": state.get("transaction", {}).get("device_id"),
        }
    ]


async def transaction_analysis_node(
    state: InvestigationState,
    *,
    service: TransactionAnalysisService | None = None,
) -> PartialState:
    """LangGraph-compatible node wrapper for transaction analysis."""

    analysis_service = service or TransactionAnalysisService()

    async def handler(current: InvestigationState) -> PartialState:
        result = await analysis_service.analyze(
            transaction_id=current["transaction_id"],
            transactions=_transactions_from_state(current),
        )
        severity = _risk_band(result["anomaly_score"])
        evidence = _evidence(result["summary"])
        return {
            "status": "fraud_analysis",
            "transaction_analysis": result,
            "fraud_score": result["anomaly_score"],
            "confidence": result["confidence"],
            "fraud_typologies": [item["indicator"] for item in result["indicators"]],
            "recommended_actions": result["recommended_actions"],
            "evidence": [evidence],
            "findings": [
                _finding(
                    severity=severity,
                    description=result["summary"],
                    evidence_id=evidence["evidence_id"],
                    confidence=result["confidence"],
                )
            ],
            "agent_executions": [_agent_execution(result["confidence"])],
            "workflow_history": [_event("Transaction analysis completed.")],
        }

    async def fallback(current: InvestigationState) -> PartialState:
        return {
            "status": "fraud_analysis",
            "fraud_score": 50.0,
            "fraud_typologies": ["transaction_analysis_fallback"],
            "recommended_actions": ["analyst_review"],
            "workflow_history": [_event("Transaction analysis fallback used.")],
        }

    return await with_node_resilience(
        "transaction_analysis",
        state,
        handler,
        fallback,
        policy=RetryPolicy(
            max_attempts=2,
            retry_route="evidence_expansion",
            fallback_name="deterministic_fallback",
        ),
    )
