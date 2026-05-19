from typing import NotRequired, TypedDict

from app.core.graph.state_schemas.enums import (
    ApprovalStatus,
    EscalationLevel,
    WorkflowEventStatus,
)


class WorkflowEvent(TypedDict):
    """Append-only workflow history event for audit and replay diagnostics."""

    event_id: str
    node: str
    status: WorkflowEventStatus
    message: str
    created_at: str
    route: NotRequired[str]
    input_hash: NotRequired[str]
    output_hash: NotRequired[str]


class ApprovalRequest(TypedDict):
    """Human approval checkpoint payload."""

    approval_id: str
    checkpoint_name: str
    reason: str
    required_role: str
    status: ApprovalStatus
    requested_at: NotRequired[str]
    decided_at: NotRequired[str]
    reviewer_id: NotRequired[str]
    reviewer_rationale: NotRequired[str]


class EscalationDecision(TypedDict):
    """Structured escalation state for case-management and audit routing."""

    escalation_id: str
    level: EscalationLevel
    reason: str
    required_role: str
    created_at: str
    resolved_at: NotRequired[str]
    approval_id: NotRequired[str]
    action_refs: NotRequired[list[str]]
