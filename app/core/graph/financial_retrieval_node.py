from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.core.graph.retry import RetryPolicy, with_node_resilience
from app.core.graph.state import (
    AgentExecution,
    EvidenceRef,
    FinancialRetrievalResponse,
    InvestigationFinding,
    InvestigationState,
    WorkflowEvent,
)
from app.services.financial_retrieval import FinancialRetrievalAgentService

PartialState = dict[str, Any]


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _event(message: str) -> WorkflowEvent:
    return {
        "event_id": f"evt_{uuid4().hex}",
        "node": "financial_retrieval",
        "status": "completed",
        "message": message,
        "created_at": _now(),
    }


def _query_from_state(state: InvestigationState) -> str:
    risk_band = state.get("risk_band", "unknown")
    fraud_typologies = ", ".join(state.get("fraud_typologies", []))
    compliance_flags = ", ".join(state.get("compliance_flags", []))
    return (
        f"Retrieve compliance, AML, audit, governance, and SEC evidence for "
        f"transaction {state['transaction_id']} with risk {risk_band}, "
        f"fraud signals {fraud_typologies}, and compliance flags {compliance_flags}."
    )


def _evidence_refs(response: FinancialRetrievalResponse) -> list[EvidenceRef]:
    refs: list[EvidenceRef] = []
    for evidence in response["evidence"]:
        citation = evidence["citation"]
        refs.append(
            {
                "evidence_id": evidence["evidence_id"],
                "evidence_type": "external_intelligence",
                "source_system": "financial_retrieval_agent",
                "uri": citation["source_uri"],
                "collected_at": _now(),
                "summary": f"{citation['attribution']}: {citation['quote']}",
            }
        )
    return refs


def _finding(response: FinancialRetrievalResponse, evidence_ids: list[str]) -> InvestigationFinding:
    severity = "low"
    if response["confidence"] >= 0.75:
        severity = "medium"
    return {
        "finding_id": f"finding_{uuid4().hex}",
        "category": "compliance",
        "severity": severity,
        "description": response["answer_summary"],
        "evidence_ids": evidence_ids,
        "confidence": response["confidence"],
        "source_node": "financial_retrieval",
    }


def _agent_execution(response: FinancialRetrievalResponse) -> AgentExecution:
    return {
        "execution_id": f"exec_{uuid4().hex}",
        "agent_role": "compliance_reviewer",
        "node": "financial_retrieval",
        "provider": "rag_retrieval_service",
        "model": "hashing-embedding-rerank-v1",
        "started_at": _now(),
        "completed_at": _now(),
        "confidence": response["confidence"],
        "status": "success",
    }


async def financial_retrieval_node(
    state: InvestigationState,
    *,
    service: FinancialRetrievalAgentService | None = None,
) -> PartialState:
    """LangGraph-compatible RAG node for grounded financial evidence retrieval."""

    retrieval_service = service or FinancialRetrievalAgentService()

    async def handler(current: InvestigationState) -> PartialState:
        response = await retrieval_service.retrieve(query=_query_from_state(current))
        evidence_refs = _evidence_refs(response)
        return {
            "status": "compliance_validation",
            "financial_retrieval": response,
            "evidence": evidence_refs,
            "findings": [
                _finding(response, [item["evidence_id"] for item in evidence_refs])
            ],
            "agent_executions": [_agent_execution(response)],
            "workflow_history": [_event("Financial retrieval completed with citations.")],
        }

    async def fallback(current: InvestigationState) -> PartialState:
        return {
            "status": "compliance_validation",
            "workflow_history": [_event("Financial retrieval fallback used.")],
        }

    return await with_node_resilience(
        "financial_retrieval",
        state,
        handler,
        fallback,
        policy=RetryPolicy(
            max_attempts=2,
            retry_route="evidence_expansion",
            fallback_name="deterministic_fallback",
        ),
    )
