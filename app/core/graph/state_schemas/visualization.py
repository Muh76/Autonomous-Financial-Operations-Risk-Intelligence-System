from typing import Literal, NotRequired, TypedDict


TraceStatus = Literal[
    "pending",
    "running",
    "success",
    "failed",
    "retrying",
    "fallback",
    "skipped",
    "interrupted",
]
TimelineEventType = Literal[
    "workflow_started",
    "node_started",
    "node_completed",
    "node_failed",
    "edge_traversed",
    "retry_scheduled",
    "fallback_used",
    "escalation_requested",
    "approval_requested",
    "approval_decided",
    "workflow_paused",
    "workflow_resumed",
    "workflow_completed",
]


class GraphNodeMetadata(TypedDict):
    """Static node metadata used by workflow visualization clients."""

    node_id: str
    label: str
    node_type: str
    agent_role: NotRequired[str]
    description: NotRequired[str]
    timeout_seconds: NotRequired[float]
    retryable: NotRequired[bool]
    requires_human: NotRequired[bool]
    group: NotRequired[str]


class GraphEdgeMetadata(TypedDict):
    """Static edge metadata for graph layout and route explanation."""

    edge_id: str
    source: str
    target: str
    edge_type: str
    condition: NotRequired[str]
    label: NotRequired[str]


class NodeExecutionTrace(TypedDict):
    """Runtime trace for one node execution attempt."""

    trace_id: str
    node_id: str
    status: TraceStatus
    started_at: str
    completed_at: NotRequired[str]
    duration_ms: NotRequired[int]
    attempt: NotRequired[int]
    confidence: NotRequired[float]
    output_fields: NotRequired[list[str]]
    error_type: NotRequired[str]
    error_message: NotRequired[str]


class EdgeTraversalTrace(TypedDict):
    """Runtime record showing which graph edge was traversed."""

    traversal_id: str
    source: str
    target: str
    traversed_at: str
    route: NotRequired[str]
    reason: NotRequired[str]
    confidence: NotRequired[float]


class RetryVisualizationTrace(TypedDict):
    """Retry-focused trace fragment for dashboards."""

    retry_id: str
    node_id: str
    attempt: int
    max_attempts: int
    retryable: bool
    failure_class: NotRequired[str]
    fallback_used: NotRequired[str]
    next_retry_route: NotRequired[str]


class EscalationPathTrace(TypedDict):
    """Escalation path record for replaying high-risk routes."""

    escalation_id: str
    source_node: str
    escalation_level: str
    required_role: str
    reason: str
    created_at: str
    approval_id: NotRequired[str]
    resolved_at: NotRequired[str]


class WorkflowTimelineEvent(TypedDict):
    """Dashboard-ready timeline item built from workflow traces."""

    event_id: str
    event_type: TimelineEventType
    label: str
    occurred_at: str
    node_id: NotRequired[str]
    edge_id: NotRequired[str]
    severity: NotRequired[str]
    summary: NotRequired[str]
    metadata: NotRequired[dict[str, str | int | float | bool | None]]


class WorkflowVisualizationMetadata(TypedDict):
    """Complete visualization read model for a workflow run."""

    workflow_id: str
    case_id: str
    tenant_id: str
    status: str
    nodes: list[GraphNodeMetadata]
    edges: list[GraphEdgeMetadata]
    node_traces: list[NodeExecutionTrace]
    edge_traversals: list[EdgeTraversalTrace]
    retries: list[RetryVisualizationTrace]
    escalations: list[EscalationPathTrace]
    timeline: list[WorkflowTimelineEvent]
