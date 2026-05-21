from operator import add
from typing import Annotated, NotRequired, TypedDict

from app.core.graph.state_schemas import (
    AgentExecution,
    AgentRole,
    ApprovalRequest,
    ApprovalStatus,
    CaseStatus,
    ComplianceReviewState,
    ComplianceValidationResult,
    ConfidenceAssessment,
    CriticValidationResult,
    EscalationDecision,
    EscalationLevel,
    EdgeTraversalTrace,
    EvidenceRef,
    EvidenceType,
    ExecutiveReport,
    FailureClass,
    FinancialRetrievalResponse,
    FindingCategory,
    FraudDetectionResult,
    InvestigationFinding,
    InvestigationMemory,
    NodeExecutionTrace,
    NodeError,
    NodeExecutionStatus,
    NodeResult,
    OperationalRiskScore,
    RetryState,
    RiskAssessment,
    RiskBand,
    SubjectProfile,
    TransactionAnalysisResult,
    TransactionContext,
    TransactionObservation,
    WorkflowEvent,
    WorkflowEventStatus,
    WorkflowRoute,
    WorkflowTimelineEvent,
)


class InvestigationState(TypedDict):
    """Canonical LangGraph state for durable financial investigation workflows.

    The top-level fields are optimized for LangGraph reducers and routing. Nested fields provide
    stable enterprise contracts for API, persistence, audit, and future subgraph boundaries.
    """

    case_id: str
    tenant_id: str
    thread_id: str
    transaction_id: str
    workflow_version: str
    schema_version: str
    status: CaseStatus

    customer_id: NotRequired[str]
    account_ids: NotRequired[list[str]]
    merchant_id: NotRequired[str]
    transaction_amount: NotRequired[float]
    transaction_currency: NotRequired[str]
    jurisdiction: NotRequired[str]

    transaction: NotRequired[TransactionContext]
    transaction_history: NotRequired[list[TransactionObservation]]
    subject: NotRequired[SubjectProfile]
    compliance_review: NotRequired[ComplianceReviewState]
    compliance_validation: NotRequired[ComplianceValidationResult]
    risk_assessment: NotRequired[RiskAssessment]
    operational_risk: NotRequired[OperationalRiskScore]
    confidence_assessment: NotRequired[ConfidenceAssessment]
    critic_validation: NotRequired[CriticValidationResult]
    persistent_memory: NotRequired[InvestigationMemory]
    financial_retrieval: NotRequired[FinancialRetrievalResponse]
    transaction_analysis: NotRequired[TransactionAnalysisResult]
    fraud_detection: NotRequired[FraudDetectionResult]

    transaction_snapshot: NotRequired[dict[str, str | int | float | bool | None]]
    customer_profile: NotRequired[dict[str, str | int | float | bool | None]]
    account_history_summary: NotRequired[str]
    merchant_profile: NotRequired[dict[str, str | int | float | bool | None]]
    relationship_graph_summary: NotRequired[str]

    evidence: Annotated[list[EvidenceRef], add]
    findings: Annotated[list[InvestigationFinding], add]
    workflow_history: Annotated[list[WorkflowEvent], add]
    node_errors: Annotated[list[NodeError], add]
    approvals: Annotated[list[ApprovalRequest], add]
    escalations: Annotated[list[EscalationDecision], add]
    node_results: Annotated[list[NodeResult], add]
    agent_executions: Annotated[list[AgentExecution], add]
    node_traces: Annotated[list[NodeExecutionTrace], add]
    edge_traversals: Annotated[list[EdgeTraversalTrace], add]
    timeline_events: Annotated[list[WorkflowTimelineEvent], add]

    retry_counts: dict[str, int]
    retry_state: dict[str, RetryState]
    fallback_used: dict[str, str]

    fraud_score: NotRequired[float]
    compliance_score: NotRequired[float]
    aggregate_risk_score: NotRequired[float]
    risk_band: NotRequired[RiskBand]
    escalation_level: NotRequired[EscalationLevel]
    confidence: NotRequired[float]

    fraud_typologies: NotRequired[list[str]]
    compliance_flags: NotRequired[list[str]]
    recommended_actions: NotRequired[list[str]]
    critic_passed: NotRequired[bool]
    critic_notes: NotRequired[list[str]]
    next_route: NotRequired[WorkflowRoute]

    report_draft: NotRequired[str]
    final_report_uri: NotRequired[str]
    executive_report: NotRequired[ExecutiveReport]


__all__ = [
    "AgentExecution",
    "AgentRole",
    "ApprovalRequest",
    "ApprovalStatus",
    "CaseStatus",
    "ComplianceReviewState",
    "ComplianceValidationResult",
    "ConfidenceAssessment",
    "CriticValidationResult",
    "EscalationDecision",
    "EscalationLevel",
    "EvidenceRef",
    "EvidenceType",
    "ExecutiveReport",
    "FailureClass",
    "FinancialRetrievalResponse",
    "FindingCategory",
    "FraudDetectionResult",
    "InvestigationFinding",
    "InvestigationMemory",
    "InvestigationState",
    "NodeError",
    "NodeExecutionTrace",
    "NodeExecutionStatus",
    "NodeResult",
    "OperationalRiskScore",
    "RetryState",
    "RiskAssessment",
    "RiskBand",
    "SubjectProfile",
    "TransactionContext",
    "TransactionAnalysisResult",
    "TransactionObservation",
    "EdgeTraversalTrace",
    "WorkflowEvent",
    "WorkflowEventStatus",
    "WorkflowRoute",
    "WorkflowTimelineEvent",
]
