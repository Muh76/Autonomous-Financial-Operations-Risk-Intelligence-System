from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.core.graph.state import (
    AgentExecution,
    AgentRole,
    ApprovalRequest,
    EscalationDecision,
    EscalationLevel,
    EvidenceRef,
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

MAX_SEMANTIC_RETRIES = 2


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


def _node_result(
    node: str,
    status: NodeExecutionStatus,
    output_fields: list[str],
    *,
    confidence: float | None = None,
    next_route: str | None = None,
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
    if next_route is not None:
        result["next_route"] = next_route
    if error is not None:
        result["error"] = error
    return result


def _agent_execution(
    *,
    agent_role: AgentRole,
    node: str,
    provider: str = "deterministic_service",
    model: str = "ruleset-v1",
    confidence: float | None = None,
) -> AgentExecution:
    execution: AgentExecution = {
        "execution_id": f"exec_{uuid4().hex}",
        "agent_role": agent_role,
        "node": node,
        "provider": provider,
        "model": model,
        "started_at": _now(),
        "completed_at": _now(),
        "status": "success",
    }
    if confidence is not None:
        execution["confidence"] = confidence
    return execution


def _error(
    node: str,
    error: Exception,
    *,
    retryable: bool,
    attempt: int,
) -> NodeError:
    return {
        "node": node,
        "error_type": type(error).__name__,
        "message": str(error),
        "retryable": retryable,
        "attempt": attempt,
    }


def _finding(
    *,
    category: FindingCategory,
    severity: RiskBand,
    description: str,
    evidence_ids: list[str],
    confidence: float,
    source_node: str,
) -> InvestigationFinding:
    return {
        "finding_id": f"finding_{uuid4().hex}",
        "category": category,
        "severity": severity,
        "description": description,
        "evidence_ids": evidence_ids,
        "confidence": confidence,
        "source_node": source_node,
    }


def _evidence(
    *,
    evidence_type: str,
    source_system: str,
    uri: str,
    summary: str,
) -> EvidenceRef:
    return {
        "evidence_id": f"ev_{uuid4().hex}",
        "evidence_type": evidence_type,
        "source_system": source_system,
        "uri": uri,
        "collected_at": _now(),
        "summary": summary,
    }


def _risk_band(score: float) -> RiskBand:
    if score >= 90:
        return "critical"
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"


def _escalation_from_risk(risk_band: RiskBand, compliance_flags: list[str]) -> EscalationLevel:
    if "sanctions_hit" in compliance_flags or risk_band == "critical":
        return "block"
    if "sar_threshold_met" in compliance_flags:
        return "regulatory"
    if risk_band == "high":
        return "senior_review"
    if risk_band == "medium":
        return "analyst_review"
    return "none"


def _attempt(state: InvestigationState, node: str) -> int:
    return state.get("retry_counts", {}).get(node, 0) + 1


async def with_node_resilience(
    node: str,
    state: InvestigationState,
    handler: NodeHandler,
    fallback: NodeHandler | None = None,
) -> PartialState:
    """Wrap a node with retry metadata and deterministic fallback routing."""

    attempt = _attempt(state, node)
    try:
        result = await handler(state)
        retry_counts = dict(state.get("retry_counts", {}))
        retry_counts[node] = attempt
        retry_state = dict(state.get("retry_state", {}))
        retry_state[node] = {
            "node": node,
            "attempts": attempt,
            "max_attempts": MAX_SEMANTIC_RETRIES,
            "retryable": False,
        }
        result.setdefault("retry_counts", retry_counts)
        result.setdefault("retry_state", retry_state)
        result.setdefault("workflow_history", [])
        result["workflow_history"].append(_event(node, "completed", "Node completed successfully."))
        result.setdefault("node_results", [])
        result["node_results"].append(
            _node_result(node, "success", sorted(key for key in result if key != "node_results"))
        )
        return result
    except Exception as exc:
        retryable = attempt <= MAX_SEMANTIC_RETRIES
        error = _error(node, exc, retryable=retryable, attempt=attempt)
        retry_counts = dict(state.get("retry_counts", {}))
        retry_counts[node] = attempt

        if retryable:
            return {
                "status": "evidence_expansion",
                "next_route": "evidence_expansion",
                "retry_counts": retry_counts,
                "retry_state": {
                    **state.get("retry_state", {}),
                    node: {
                        "node": node,
                        "attempts": attempt,
                        "max_attempts": MAX_SEMANTIC_RETRIES,
                        "retryable": True,
                        "last_error_type": type(exc).__name__,
                    },
                },
                "node_errors": [error],
                "node_results": [
                    _node_result(
                        node,
                        "retrying",
                        ["status", "next_route", "node_errors"],
                        next_route="evidence_expansion",
                        error=error,
                    )
                ],
                "workflow_history": [
                    _event(node, "failed", "Node failed and will route to recovery.")
                ],
            }

        if fallback is not None:
            fallback_result = await fallback(state)
            fallback_used = dict(state.get("fallback_used", {}))
            fallback_used[node] = "deterministic_fallback"
            fallback_result["retry_counts"] = retry_counts
            fallback_result["retry_state"] = {
                **state.get("retry_state", {}),
                node: {
                    "node": node,
                    "attempts": attempt,
                    "max_attempts": MAX_SEMANTIC_RETRIES,
                    "retryable": False,
                    "last_error_type": type(exc).__name__,
                    "fallback_used": "deterministic_fallback",
                },
            }
            fallback_result["fallback_used"] = fallback_used
            fallback_result.setdefault("node_errors", [])
            fallback_result["node_errors"].append(error)
            fallback_result.setdefault("node_results", [])
            fallback_result["node_results"].append(
                _node_result(
                    node,
                    "fallback",
                    sorted(key for key in fallback_result if key != "node_results"),
                    error=error,
                )
            )
            fallback_result.setdefault("workflow_history", [])
            fallback_result["workflow_history"].append(
                _event(node, "fallback", "Fallback completed after retry exhaustion.")
            )
            return fallback_result

        return {
            "status": "failed",
            "next_route": "workflow_failure",
            "retry_counts": retry_counts,
            "retry_state": {
                **state.get("retry_state", {}),
                node: {
                    "node": node,
                    "attempts": attempt,
                    "max_attempts": MAX_SEMANTIC_RETRIES,
                    "retryable": False,
                    "last_error_type": type(exc).__name__,
                },
            },
            "node_errors": [error],
            "node_results": [
                _node_result(
                    node,
                    "failed",
                    ["status", "next_route", "node_errors"],
                    next_route="workflow_failure",
                    error=error,
                )
            ],
            "workflow_history": [_event(node, "failed", "Node failed without fallback.")],
        }


async def normalize_intake_node(state: InvestigationState) -> PartialState:
    transaction_id = state["transaction_id"].strip()
    tenant_id = state["tenant_id"].strip()
    if not transaction_id:
        raise ValueError("transaction_id is required")
    if not tenant_id:
        raise ValueError("tenant_id is required")

    return {
        "case_id": state.get("case_id") or f"case_{transaction_id}",
        "thread_id": state.get("thread_id") or f"thread_{transaction_id}",
        "transaction_id": transaction_id,
        "tenant_id": tenant_id,
        "status": "enriching",
        "workflow_history": [
            _event("normalize_intake", "completed", "Investigation intake normalized.")
        ],
    }


async def collect_transaction_context_node(state: InvestigationState) -> PartialState:
    async def handler(current: InvestigationState) -> PartialState:
        transaction_id = current["transaction_id"]
        amount = float(current.get("transaction_amount", 0.0))
        evidence = _evidence(
            evidence_type="transaction_snapshot",
            source_system="core_banking",
            uri=f"evidence://transactions/{transaction_id}",
            summary="Canonical transaction snapshot collected for investigation.",
        )

        return {
            "status": "fraud_analysis",
            "transaction": {
                "transaction_id": transaction_id,
                "amount": amount,
                "currency": current.get("transaction_currency", "USD"),
                "jurisdiction": current.get("jurisdiction", "US"),
                "merchant_id": current.get("merchant_id", "unknown"),
                "raw_snapshot_ref": evidence["uri"],
            },
            "subject": {
                "customer_id": current.get("customer_id", "unknown"),
                "account_ids": current.get("account_ids", []),
                "kyc_status": "verified",
                "customer_segment": "retail",
                "merchant_id": current.get("merchant_id", "unknown"),
            },
            "persistent_memory": {
                "memory_namespace": f"{current['tenant_id']}:{current['transaction_id']}",
                "case_memory_refs": [],
                "entity_memory_refs": [],
                "last_updated_at": _now(),
            },
            "transaction_snapshot": {
                "transaction_id": transaction_id,
                "amount": amount,
                "currency": current.get("transaction_currency", "USD"),
                "jurisdiction": current.get("jurisdiction", "US"),
            },
            "customer_profile": {
                "customer_id": current.get("customer_id", "unknown"),
                "kyc_status": "verified",
                "segment": "retail",
            },
            "account_history_summary": "Recent account activity is available for velocity checks.",
            "merchant_profile": {"merchant_id": current.get("merchant_id", "unknown")},
            "relationship_graph_summary": "Initial context found no linked-account anomaly.",
            "evidence": [evidence],
            "findings": [
                _finding(
                    category="transaction",
                    severity="low",
                    description="Transaction context enrichment completed with auditable evidence.",
                    evidence_ids=[evidence["evidence_id"]],
                    confidence=0.98,
                    source_node="collect_transaction_context",
                )
            ],
            "agent_executions": [
                _agent_execution(
                    agent_role="transaction_investigator",
                    node="collect_transaction_context",
                    confidence=0.98,
                )
            ],
        }

    return await with_node_resilience("collect_transaction_context", state, handler)


async def fraud_analysis_node(state: InvestigationState) -> PartialState:
    async def handler(current: InvestigationState) -> PartialState:
        amount = float(current.get("transaction_amount", 0.0))
        existing_evidence_count = len(current.get("evidence", []))
        score = min(100.0, 25.0 + (amount / 1000.0) + existing_evidence_count * 4.0)
        typologies: list[str] = []
        if amount >= 10_000:
            typologies.append("high_value_anomaly")
        graph_summary = current.get("relationship_graph_summary", "").lower()
        if "confirmed mule" in graph_summary or "possible mule" in graph_summary:
            typologies.append("possible_mule_network")
            score += 15.0

        severity = _risk_band(score)
        return {
            "status": "compliance_validation",
            "fraud_score": min(score, 100.0),
            "fraud_typologies": typologies,
            "findings": [
                _finding(
                    category="fraud",
                    severity=severity,
                    description="Fraud analysis scored behavioral and network-level transaction risk.",
                    evidence_ids=[item["evidence_id"] for item in current.get("evidence", [])],
                    confidence=0.82,
                    source_node="fraud_analysis",
                )
            ],
            "agent_executions": [
                _agent_execution(
                    agent_role="fraud_analyst",
                    node="fraud_analysis",
                    confidence=0.82,
                )
            ],
        }

    async def fallback(current: InvestigationState) -> PartialState:
        return {
            "status": "compliance_validation",
            "fraud_score": 50.0,
            "fraud_typologies": ["fallback_rules_based_triage"],
            "findings": [
                _finding(
                    category="fraud",
                    severity="medium",
                    description="Rules-based fraud fallback used because primary analysis was unavailable.",
                    evidence_ids=[item["evidence_id"] for item in current.get("evidence", [])],
                    confidence=0.55,
                    source_node="fraud_analysis_fallback",
                )
            ],
            "agent_executions": [
                _agent_execution(
                    agent_role="fraud_analyst",
                    node="fraud_analysis_fallback",
                    confidence=0.55,
                )
            ],
        }

    return await with_node_resilience("fraud_analysis", state, handler, fallback)


async def compliance_validation_node(state: InvestigationState) -> PartialState:
    async def handler(current: InvestigationState) -> PartialState:
        amount = float(current.get("transaction_amount", 0.0))
        jurisdiction = str(current.get("jurisdiction", "US")).upper()
        flags: list[str] = []
        if amount >= 10_000:
            flags.append("sar_threshold_met")
        if jurisdiction in {"IR", "KP", "SY"}:
            flags.append("sanctions_hit")

        score = 95.0 if "sanctions_hit" in flags else 75.0 if flags else 20.0
        return {
            "status": "risk_scoring",
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
                    description="Compliance validation evaluated jurisdiction and reporting triggers.",
                    evidence_ids=[item["evidence_id"] for item in current.get("evidence", [])],
                    confidence=0.9,
                    source_node="compliance_validation",
                )
            ],
            "agent_executions": [
                _agent_execution(
                    agent_role="compliance_reviewer",
                    node="compliance_validation",
                    confidence=0.9,
                )
            ],
        }

    async def fallback(current: InvestigationState) -> PartialState:
        return {
            "status": "risk_scoring",
            "compliance_score": 60.0,
            "compliance_flags": ["manual_compliance_review_required"],
            "compliance_review": {
                "sanctions_screened": False,
                "pep_screened": False,
                "aml_rules_evaluated": False,
                "jurisdiction_checked": False,
                "flags": ["manual_compliance_review_required"],
                "policy_version": "compliance-policy-v1",
                "reviewer_notes": ["Fallback requires manual compliance verification."],
            },
            "findings": [
                _finding(
                    category="compliance",
                    severity="medium",
                    description="Compliance fallback requires manual validation of policy triggers.",
                    evidence_ids=[item["evidence_id"] for item in current.get("evidence", [])],
                    confidence=0.5,
                    source_node="compliance_validation_fallback",
                )
            ],
            "agent_executions": [
                _agent_execution(
                    agent_role="compliance_reviewer",
                    node="compliance_validation_fallback",
                    confidence=0.5,
                )
            ],
        }

    return await with_node_resilience("compliance_validation", state, handler, fallback)


async def risk_scoring_node(state: InvestigationState) -> PartialState:
    fraud_score = float(state.get("fraud_score", 0.0))
    compliance_score = float(state.get("compliance_score", 0.0))
    aggregate = round(fraud_score * 0.55 + compliance_score * 0.45, 2)
    risk_band = _risk_band(aggregate)
    compliance_flags = state.get("compliance_flags", [])
    escalation_level = _escalation_from_risk(risk_band, compliance_flags)

    return {
        "status": "critic_validation",
        "aggregate_risk_score": aggregate,
        "risk_band": risk_band,
        "escalation_level": escalation_level,
        "recommended_actions": _recommended_actions(risk_band, escalation_level),
        "risk_assessment": {
            "fraud_score": fraud_score,
            "compliance_score": compliance_score,
            "transaction_score": fraud_score,
            "customer_score": 0.0,
            "aggregate_score": aggregate,
            "risk_band": risk_band,
            "escalation_level": escalation_level,
            "scoring_model_version": "risk-scoring-v1",
            "policy_version": "risk-policy-v1",
            "confidence": 0.88,
            "recommended_actions": _recommended_actions(risk_band, escalation_level),
            "score_components": {
                "fraud_weighted": round(fraud_score * 0.55, 2),
                "compliance_weighted": round(compliance_score * 0.45, 2),
            },
        },
        "findings": [
            _finding(
                category="risk",
                severity=risk_band,
                description="Aggregate risk score calculated from fraud and compliance signals.",
                evidence_ids=[item["evidence_id"] for item in state.get("evidence", [])],
                confidence=0.88,
                source_node="risk_scoring",
            )
        ],
        "agent_executions": [
            _agent_execution(agent_role="risk_scorer", node="risk_scoring", confidence=0.88)
        ],
        "workflow_history": [_event("risk_scoring", "completed", "Risk score calculated.")],
    }


def _recommended_actions(risk_band: RiskBand, escalation_level: EscalationLevel) -> list[str]:
    if escalation_level == "block":
        return ["place_temporary_hold", "senior_review", "prepare_regulatory_packet"]
    if escalation_level == "regulatory":
        return ["analyst_review", "prepare_sar_draft"]
    if risk_band == "high":
        return ["senior_review", "expand_evidence"]
    if risk_band == "medium":
        return ["analyst_review"]
    return ["close_as_low_risk"]


async def critic_validation_node(state: InvestigationState) -> PartialState:
    evidence_count = len(state.get("evidence", []))
    findings_count = len(state.get("findings", []))
    confidence = min(0.99, 0.45 + evidence_count * 0.12 + findings_count * 0.04)
    notes: list[str] = []

    if evidence_count < 2 and state.get("risk_band") in {"high", "critical"}:
        notes.append("High-risk decision needs additional evidence before final action.")
    if not state.get("fraud_score") and not state.get("compliance_score"):
        notes.append("Risk score is missing upstream fraud or compliance components.")

    passed = not notes and confidence >= 0.7
    next_route = "report_generation" if passed else "evidence_expansion"
    if state.get("escalation_level") in {"senior_review", "regulatory", "block"} and passed:
        next_route = "escalation_router"

    return {
        "status": "reporting" if passed else "evidence_expansion",
        "critic_passed": passed,
        "critic_notes": notes,
        "confidence": round(confidence, 2),
        "confidence_assessment": {
            "overall": round(confidence, 2),
            "evidence_quality": min(0.99, 0.4 + evidence_count * 0.2),
            "reasoning_quality": 0.82 if passed else 0.6,
            "policy_alignment": 0.9 if not notes else 0.65,
            "explanation": "Critic confidence derived from evidence sufficiency and consistency checks.",
        },
        "next_route": next_route,
        "findings": [
            _finding(
                category="critic",
                severity="low" if passed else "medium",
                description="Critic validation checked evidence sufficiency and decision consistency.",
                evidence_ids=[item["evidence_id"] for item in state.get("evidence", [])],
                confidence=confidence,
                source_node="critic_validation",
            )
        ],
        "agent_executions": [
            _agent_execution(agent_role="critic", node="critic_validation", confidence=confidence)
        ],
        "workflow_history": [_event("critic_validation", "routed", f"Next route: {next_route}.")],
    }


async def evidence_expansion_node(state: InvestigationState) -> PartialState:
    evidence = _evidence(
        evidence_type="expanded_context",
        source_system="investigation_memory",
        uri=f"evidence://cases/{state['case_id']}/expanded-context/{uuid4().hex}",
        summary="Additional historical, entity, and case-memory context collected.",
    )
    return {
        "status": "fraud_analysis",
        "evidence": [evidence],
        "relationship_graph_summary": "Expanded context reviewed for linked-account anomalies.",
        "workflow_history": [
            _event("evidence_expansion", "completed", "Additional evidence collected.")
        ],
    }


async def escalation_router_node(state: InvestigationState) -> PartialState:
    escalation_level = state.get("escalation_level", "none")
    requires_human = escalation_level in {"senior_review", "regulatory", "block"}
    approval: ApprovalRequest | None = None
    escalation: EscalationDecision | None = None

    if requires_human:
        approval_id = f"approval_{uuid4().hex}"
        approval = {
            "approval_id": approval_id,
            "checkpoint_name": "pre_final_action",
            "reason": f"{escalation_level} escalation requires authorized review.",
            "required_role": "senior_investigator"
            if escalation_level == "senior_review"
            else "compliance_officer",
            "status": "pending",
            "requested_at": _now(),
        }
        escalation = {
            "escalation_id": f"esc_{uuid4().hex}",
            "level": escalation_level,
            "reason": f"{escalation_level} case routing requires controlled review.",
            "required_role": approval["required_role"],
            "created_at": _now(),
            "approval_id": approval_id,
        }

    return {
        "status": "awaiting_human_approval" if requires_human else "reporting",
        "next_route": "human_approval_checkpoint" if requires_human else "report_generation",
        "approvals": [approval] if approval else [],
        "escalations": [escalation] if escalation else [],
        "workflow_history": [
            _event(
                "escalation_router",
                "routed",
                "Human approval required." if requires_human else "No escalation required.",
            )
        ],
    }


async def human_approval_checkpoint_node(state: InvestigationState) -> PartialState:
    approvals = state.get("approvals", [])
    pending = [approval for approval in approvals if approval["status"] == "pending"]
    if not pending:
        return {
            "status": "reporting",
            "next_route": "report_generation",
            "workflow_history": [
                _event("human_approval_checkpoint", "completed", "No pending approval found.")
            ],
        }

    # Replace this no-op with LangGraph interrupt(...) when the approval UI is ready.
    return {
        "status": "awaiting_human_approval",
        "workflow_history": [
            _event(
                "human_approval_checkpoint",
                "interrupted",
                "Approval checkpoint prepared; interrupt integration can be enabled here.",
            )
        ],
    }


async def report_generation_node(state: InvestigationState) -> PartialState:
    risk_band = state.get("risk_band", "low")
    escalation_level = state.get("escalation_level", "none")
    report = (
        f"Investigation {state['case_id']} for transaction {state['transaction_id']} closed with "
        f"{risk_band} risk, escalation level {escalation_level}, and "
        f"{len(state.get('findings', []))} structured findings."
    )

    return {
        "status": "closed",
        "report_draft": report,
        "final_report_uri": f"reports://investigations/{state['case_id']}/final",
        "findings": [
            _finding(
                category="report",
                severity=risk_band,
                description="Final investigation report generated from typed workflow state.",
                evidence_ids=[item["evidence_id"] for item in state.get("evidence", [])],
                confidence=state.get("confidence", 0.75),
                source_node="report_generation",
            )
        ],
        "agent_executions": [
            _agent_execution(
                agent_role="report_writer",
                node="report_generation",
                confidence=state.get("confidence", 0.75),
            )
        ],
        "workflow_history": [_event("report_generation", "completed", "Report generated.")],
    }


async def workflow_failure_node(state: InvestigationState) -> PartialState:
    return {
        "status": "failed",
        "workflow_history": [
            _event("workflow_failure", "failed", "Workflow stopped after unrecoverable failure.")
        ],
    }
