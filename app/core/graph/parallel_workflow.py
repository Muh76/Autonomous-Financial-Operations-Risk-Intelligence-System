import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from time import perf_counter
from typing import Any
from uuid import uuid4

from langgraph.graph import END, StateGraph

from app.core.graph.state import (
    AgentExecution,
    AgentRole,
    CaseStatus,
    FindingCategory,
    InvestigationFinding,
    InvestigationState,
    NodeError,
    NodeExecutionStatus,
    NodeResult,
    RiskBand,
    WorkflowEvent,
    WorkflowEventStatus,
)
from app.core.graph.workflow import SCHEMA_VERSION, WORKFLOW_VERSION

PartialState = dict[str, Any]
NodeHandler = Callable[[InvestigationState], Awaitable[PartialState]]


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _event(node: str, status: WorkflowEventStatus, message: str) -> WorkflowEvent:
    return {
        "event_id": f"evt_{uuid4().hex}",
        "node": node,
        "status": status,
        "message": message,
        "created_at": _now(),
    }


def _node_error(
    *,
    node: str,
    message: str,
    error_type: str = "TimeoutError",
    retryable: bool = True,
) -> NodeError:
    return {
        "node": node,
        "error_type": error_type,
        "message": message,
        "retryable": retryable,
        "attempt": 1,
        "failure_class": "timeout" if error_type == "TimeoutError" else "unknown",
        "recoverable": retryable,
    }


def _node_result(
    node: str,
    status: NodeExecutionStatus,
    output_fields: list[str],
    *,
    confidence: float | None = None,
    error: NodeError | None = None,
) -> NodeResult:
    result: NodeResult = {
        "node": node,
        "status": status,
        "created_at": _now(),
        "output_fields": output_fields,
    }
    if confidence is not None:
        result["confidence"] = confidence
    if error is not None:
        result["error"] = error
    return result


def _agent_execution(
    *,
    agent_role: AgentRole,
    node: str,
    latency_ms: int,
    confidence: float,
    status: NodeExecutionStatus = "success",
) -> AgentExecution:
    return {
        "execution_id": f"exec_{uuid4().hex}",
        "agent_role": agent_role,
        "node": node,
        "provider": "async_agent_service",
        "model": "ruleset-v1",
        "started_at": _now(),
        "completed_at": _now(),
        "latency_ms": latency_ms,
        "confidence": confidence,
        "status": status,
    }


def _finding(
    *,
    category: FindingCategory,
    severity: RiskBand,
    description: str,
    confidence: float,
    source_node: str,
) -> InvestigationFinding:
    return {
        "finding_id": f"finding_{uuid4().hex}",
        "category": category,
        "severity": severity,
        "description": description,
        "evidence_ids": [],
        "confidence": confidence,
        "source_node": source_node,
    }


def _risk_band(score: float) -> RiskBand:
    if score >= 90:
        return "critical"
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _recommended_actions(risk_band: RiskBand, compliance_flags: list[str]) -> list[str]:
    if "sanctions_hit" in compliance_flags or risk_band == "critical":
        return ["place_temporary_hold", "senior_review", "prepare_regulatory_packet"]
    if "sar_threshold_met" in compliance_flags:
        return ["analyst_review", "prepare_sar_draft"]
    if risk_band == "high":
        return ["senior_review", "expand_evidence"]
    if risk_band == "medium":
        return ["analyst_review"]
    return ["close_as_low_risk"]


async def _run_with_timeout(
    *,
    node: str,
    state: InvestigationState,
    timeout_seconds: float,
    handler: NodeHandler,
    fallback: Callable[[NodeError], PartialState],
) -> PartialState:
    started = perf_counter()
    try:
        return await asyncio.wait_for(handler(state), timeout=timeout_seconds)
    except TimeoutError:
        elapsed_ms = round((perf_counter() - started) * 1000)
        error = _node_error(
            node=node,
            message=f"{node} timed out after {timeout_seconds:.2f}s.",
        )
        payload = fallback(error)
        payload.setdefault("node_errors", []).append(error)
        payload.setdefault("node_results", []).append(
            _node_result(node, "fallback", list(payload.keys()), error=error)
        )
        payload.setdefault("workflow_history", []).append(
            _event(node, "fallback", f"Timeout fallback used after {elapsed_ms}ms.")
        )
        return payload


async def normalize_parallel_intake_node(state: InvestigationState) -> PartialState:
    transaction_id = state["transaction_id"].strip()
    tenant_id = state["tenant_id"].strip()
    return {
        "case_id": state.get("case_id") or f"case_{transaction_id}",
        "thread_id": state.get("thread_id") or f"thread_{tenant_id}_{transaction_id}",
        "transaction_id": transaction_id,
        "tenant_id": tenant_id,
        "status": "enriching",
        "workflow_history": [
            _event("normalize_parallel_intake", "completed", "Parallel intake normalized.")
        ],
    }


async def parallel_analysis_fanout_node(state: InvestigationState) -> PartialState:
    return {
        "status": "fraud_analysis",
        "workflow_history": [
            _event(
                "parallel_analysis_fanout",
                "started",
                "Fraud analysis and compliance validation dispatched in parallel.",
            )
        ],
    }


async def parallel_fraud_analysis_node(state: InvestigationState) -> PartialState:
    async def handler(current: InvestigationState) -> PartialState:
        started = perf_counter()
        await asyncio.sleep(0)
        amount = float(current.get("transaction_amount", 0.0))
        score = min(100.0, 25.0 + amount / 1000.0)
        typologies: list[str] = []
        if amount >= 10_000:
            typologies.append("high_value_anomaly")
        if "mule" in current.get("relationship_graph_summary", "").lower():
            typologies.append("possible_mule_network")
            score = min(100.0, score + 15.0)

        confidence = 0.84
        latency_ms = round((perf_counter() - started) * 1000)
        return {
            "fraud_score": score,
            "fraud_typologies": typologies,
            "findings": [
                _finding(
                    category="fraud",
                    severity=_risk_band(score),
                    description="Parallel fraud branch scored behavior and network risk.",
                    confidence=confidence,
                    source_node="parallel_fraud_analysis",
                )
            ],
            "node_results": [
                _node_result(
                    "parallel_fraud_analysis",
                    "success",
                    ["fraud_score", "fraud_typologies", "findings"],
                    confidence=confidence,
                )
            ],
            "agent_executions": [
                _agent_execution(
                    agent_role="fraud_analyst",
                    node="parallel_fraud_analysis",
                    latency_ms=latency_ms,
                    confidence=confidence,
                )
            ],
            "workflow_history": [
                _event("parallel_fraud_analysis", "completed", "Fraud branch completed.")
            ],
        }

    def fallback(error: NodeError) -> PartialState:
        return {
            "fraud_score": 50.0,
            "fraud_typologies": ["timeout_fallback_fraud_triage"],
            "findings": [
                _finding(
                    category="fraud",
                    severity="medium",
                    description="Fraud branch used timeout fallback scoring.",
                    confidence=0.5,
                    source_node="parallel_fraud_analysis_fallback",
                )
            ],
        }

    return await _run_with_timeout(
        node="parallel_fraud_analysis",
        state=state,
        timeout_seconds=8.0,
        handler=handler,
        fallback=fallback,
    )


async def parallel_compliance_validation_node(state: InvestigationState) -> PartialState:
    async def handler(current: InvestigationState) -> PartialState:
        started = perf_counter()
        await asyncio.sleep(0)
        amount = float(current.get("transaction_amount", 0.0))
        jurisdiction = str(current.get("jurisdiction", "US")).upper()
        flags: list[str] = []
        if amount >= 10_000:
            flags.append("sar_threshold_met")
        if jurisdiction in {"IR", "KP", "SY"}:
            flags.append("sanctions_hit")

        score = 95.0 if "sanctions_hit" in flags else 75.0 if flags else 20.0
        confidence = 0.9
        latency_ms = round((perf_counter() - started) * 1000)
        return {
            "compliance_score": score,
            "compliance_flags": flags,
            "compliance_review": {
                "sanctions_screened": True,
                "pep_screened": True,
                "aml_rules_evaluated": True,
                "jurisdiction_checked": True,
                "flags": flags,
                "policy_version": "compliance-policy-v1",
            },
            "findings": [
                _finding(
                    category="compliance",
                    severity=_risk_band(score),
                    description="Parallel compliance branch evaluated sanctions and AML triggers.",
                    confidence=confidence,
                    source_node="parallel_compliance_validation",
                )
            ],
            "node_results": [
                _node_result(
                    "parallel_compliance_validation",
                    "success",
                    ["compliance_score", "compliance_flags", "compliance_review", "findings"],
                    confidence=confidence,
                )
            ],
            "agent_executions": [
                _agent_execution(
                    agent_role="compliance_reviewer",
                    node="parallel_compliance_validation",
                    latency_ms=latency_ms,
                    confidence=confidence,
                )
            ],
            "workflow_history": [
                _event(
                    "parallel_compliance_validation",
                    "completed",
                    "Compliance branch completed.",
                )
            ],
        }

    def fallback(error: NodeError) -> PartialState:
        return {
            "compliance_score": 60.0,
            "compliance_flags": ["manual_compliance_review_required"],
            "compliance_review": {
                "sanctions_screened": False,
                "pep_screened": False,
                "aml_rules_evaluated": False,
                "jurisdiction_checked": False,
                "flags": ["manual_compliance_review_required"],
                "policy_version": "compliance-policy-v1",
                "reviewer_notes": [error["message"]],
            },
            "findings": [
                _finding(
                    category="compliance",
                    severity="medium",
                    description="Compliance branch used timeout fallback review.",
                    confidence=0.5,
                    source_node="parallel_compliance_validation_fallback",
                )
            ],
        }

    return await _run_with_timeout(
        node="parallel_compliance_validation",
        state=state,
        timeout_seconds=8.0,
        handler=handler,
        fallback=fallback,
    )


async def aggregate_parallel_results_node(state: InvestigationState) -> PartialState:
    fraud_score = float(state.get("fraud_score", 0.0))
    compliance_score = float(state.get("compliance_score", 0.0))
    compliance_flags = state.get("compliance_flags", [])
    aggregate = round(fraud_score * 0.55 + compliance_score * 0.45, 2)
    risk_band = _risk_band(aggregate)
    escalation_level = "none"
    if "sanctions_hit" in compliance_flags or risk_band == "critical":
        escalation_level = "block"
    elif "sar_threshold_met" in compliance_flags:
        escalation_level = "regulatory"
    elif risk_band == "high":
        escalation_level = "senior_review"
    elif risk_band == "medium":
        escalation_level = "analyst_review"

    return {
        "status": "reporting",
        "aggregate_risk_score": aggregate,
        "risk_band": risk_band,
        "escalation_level": escalation_level,
        "recommended_actions": _recommended_actions(risk_band, compliance_flags),
        "risk_assessment": {
            "fraud_score": fraud_score,
            "compliance_score": compliance_score,
            "transaction_score": fraud_score,
            "customer_score": 0.0,
            "aggregate_score": aggregate,
            "risk_band": risk_band,
            "escalation_level": escalation_level,
            "scoring_model_version": "parallel-risk-scoring-v1",
            "policy_version": "risk-policy-v1",
            "confidence": 0.87,
            "recommended_actions": _recommended_actions(risk_band, compliance_flags),
            "score_components": {
                "fraud_weighted": round(fraud_score * 0.55, 2),
                "compliance_weighted": round(compliance_score * 0.45, 2),
            },
            "explanation": "Risk aggregated after parallel fraud and compliance branches joined.",
        },
        "findings": [
            _finding(
                category="risk",
                severity=risk_band,
                description="Parallel branch results aggregated into final risk assessment.",
                confidence=0.87,
                source_node="aggregate_parallel_results",
            )
        ],
        "node_results": [
            _node_result(
                "aggregate_parallel_results",
                "success",
                ["aggregate_risk_score", "risk_band", "escalation_level", "risk_assessment"],
                confidence=0.87,
            )
        ],
        "workflow_history": [
            _event("aggregate_parallel_results", "completed", "Parallel results aggregated.")
        ],
    }


async def parallel_report_generation_node(state: InvestigationState) -> PartialState:
    return {
        "status": "closed",
        "report_draft": (
            f"Parallel investigation {state['case_id']} completed with "
            f"{state.get('risk_band', 'low')} risk and "
            f"{state.get('escalation_level', 'none')} escalation."
        ),
        "final_report_uri": f"reports://investigations/{state['case_id']}/parallel-final",
        "workflow_history": [
            _event("parallel_report_generation", "completed", "Parallel report generated.")
        ],
    }


def build_parallel_investigation_workflow(*, checkpointer: Any | None = None) -> Any:
    """Build a fan-out/fan-in workflow where fraud and compliance run concurrently."""

    workflow = StateGraph(InvestigationState)
    workflow.add_node("normalize_parallel_intake", normalize_parallel_intake_node)
    workflow.add_node("parallel_analysis_fanout", parallel_analysis_fanout_node)
    workflow.add_node("parallel_fraud_analysis", parallel_fraud_analysis_node)
    workflow.add_node("parallel_compliance_validation", parallel_compliance_validation_node)
    workflow.add_node("aggregate_parallel_results", aggregate_parallel_results_node)
    workflow.add_node("parallel_report_generation", parallel_report_generation_node)

    workflow.set_entry_point("normalize_parallel_intake")
    workflow.add_edge("normalize_parallel_intake", "parallel_analysis_fanout")
    workflow.add_edge("parallel_analysis_fanout", "parallel_fraud_analysis")
    workflow.add_edge("parallel_analysis_fanout", "parallel_compliance_validation")
    workflow.add_edge(
        ["parallel_fraud_analysis", "parallel_compliance_validation"],
        "aggregate_parallel_results",
    )
    workflow.add_edge("aggregate_parallel_results", "parallel_report_generation")
    workflow.add_edge("parallel_report_generation", END)

    compile_options: dict[str, Any] = {}
    if checkpointer is not None:
        compile_options["checkpointer"] = checkpointer
    return workflow.compile(**compile_options)


async def run_parallel_investigation_workflow(
    transaction_id: str,
    *,
    tenant_id: str = "default",
    transaction_amount: float = 0.0,
    transaction_currency: str = "USD",
    jurisdiction: str = "US",
    checkpointer: Any | None = None,
) -> InvestigationState:
    thread_id = f"parallel_thread_{tenant_id}_{transaction_id}"
    initial_state: InvestigationState = {
        "case_id": f"case_{transaction_id}",
        "tenant_id": tenant_id,
        "thread_id": thread_id,
        "transaction_id": transaction_id,
        "workflow_version": WORKFLOW_VERSION,
        "schema_version": SCHEMA_VERSION,
        "status": "initialized",
        "transaction_amount": transaction_amount,
        "transaction_currency": transaction_currency,
        "jurisdiction": jurisdiction,
        "evidence": [],
        "findings": [],
        "workflow_history": [],
        "node_errors": [],
        "approvals": [],
        "escalations": [],
        "node_results": [],
        "agent_executions": [],
        "retry_counts": {},
        "retry_state": {},
        "fallback_used": {},
    }
    workflow = build_parallel_investigation_workflow(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id}}
    return await workflow.ainvoke(initial_state, config=config)
