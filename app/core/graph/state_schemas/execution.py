from typing import NotRequired, TypedDict

from app.core.graph.state_schemas.enums import AgentRole, NodeExecutionStatus


class NodeError(TypedDict):
    """Structured node failure metadata used for retries, fallback, and escalation."""

    node: str
    error_type: str
    message: str
    retryable: bool
    attempt: int
    provider: NotRequired[str]


class RetryState(TypedDict):
    """Retry and fallback state for one workflow node."""

    node: str
    attempts: int
    max_attempts: int
    retryable: bool
    last_error_type: NotRequired[str]
    fallback_used: NotRequired[str]


class ConfidenceAssessment(TypedDict):
    """Confidence tracking for agentic and deterministic outputs."""

    overall: float
    evidence_quality: float
    reasoning_quality: float
    policy_alignment: float
    explanation: str


class AgentExecution(TypedDict):
    """Agent/model execution record for observability and audit."""

    execution_id: str
    agent_role: AgentRole
    node: str
    provider: str
    model: str
    started_at: str
    completed_at: NotRequired[str]
    prompt_version: NotRequired[str]
    input_hash: NotRequired[str]
    output_hash: NotRequired[str]
    latency_ms: NotRequired[int]
    token_count: NotRequired[int]
    cost_usd: NotRequired[float]
    confidence: NotRequired[float]
    status: NodeExecutionStatus


class NodeResult(TypedDict):
    """Generic node result envelope for graph-level execution tracking."""

    node: str
    status: NodeExecutionStatus
    created_at: str
    output_fields: list[str]
    confidence: NotRequired[float]
    next_route: NotRequired[str]
    error: NotRequired[NodeError]
    agent_execution_id: NotRequired[str]
