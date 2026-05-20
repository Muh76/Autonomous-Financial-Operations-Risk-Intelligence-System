from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from app.core.graph.state import ApprovalRequest, InvestigationState, WorkflowEvent

ApprovalDecision = Literal["approved", "rejected"]


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _event(node: str, message: str, *, status: str = "completed") -> WorkflowEvent:
    return {
        "event_id": f"evt_{uuid4().hex}",
        "node": node,
        "status": status,
        "message": message,
        "created_at": _now(),
    }


def latest_approval_states(approvals: list[ApprovalRequest]) -> dict[str, ApprovalRequest]:
    """Return latest approval state by approval_id from an append-only approval history."""

    latest: dict[str, ApprovalRequest] = {}
    for approval in approvals:
        latest[approval["approval_id"]] = approval
    return latest


@dataclass(slots=True)
class ApprovalDecisionRequest:
    approval_id: str
    reviewer_id: str
    decision: ApprovalDecision
    rationale: str
    next_route_on_approval: str = "report_generation"
    next_route_on_rejection: str = "evidence_expansion"


class ApprovalCheckpointService:
    """Builds pause/resume state updates for human approval checkpoints."""

    def pending_approvals(self, state: InvestigationState) -> list[ApprovalRequest]:
        latest = latest_approval_states(state.get("approvals", []))
        return [approval for approval in latest.values() if approval["status"] == "pending"]

    def is_paused_for_approval(self, state: InvestigationState) -> bool:
        return state.get("status") == "awaiting_human_approval" and bool(
            self.pending_approvals(state)
        )

    def apply_decision(
        self,
        state: InvestigationState,
        request: ApprovalDecisionRequest,
    ) -> dict[str, Any]:
        latest = latest_approval_states(state.get("approvals", []))
        existing = latest.get(request.approval_id)
        if existing is None:
            raise ValueError(f"Approval {request.approval_id} was not found")
        if existing["status"] != "pending":
            raise ValueError(
                f"Approval {request.approval_id} is already {existing['status']}"
            )

        decided: ApprovalRequest = {
            **existing,
            "status": request.decision,
            "decided_at": _now(),
            "reviewer_id": request.reviewer_id,
            "reviewer_rationale": request.rationale,
        }
        if request.decision == "approved":
            next_route = request.next_route_on_approval
            workflow_status = "reporting"
            message = "Human approval granted; workflow may resume."
        else:
            next_route = request.next_route_on_rejection
            workflow_status = "evidence_expansion"
            message = "Human approval rejected; workflow routed for remediation."

        return {
            "status": workflow_status,
            "next_route": next_route,
            "approvals": [decided],
            "workflow_history": [
                _event(
                    "approval_checkpoint",
                    message,
                    status="routed",
                )
            ],
        }
