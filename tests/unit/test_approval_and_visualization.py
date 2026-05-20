import pytest

from app.core.graph.state import InvestigationState
from app.services.approval_checkpoints import (
    ApprovalCheckpointService,
    ApprovalDecisionRequest,
    latest_approval_states,
)
from app.services.workflow_visualization import WorkflowVisualizationService

pytestmark = pytest.mark.unit


def test_approval_decision_appends_latest_status(
    high_risk_state: InvestigationState,
) -> None:
    state = {
        **high_risk_state,
        "status": "awaiting_human_approval",
        "approvals": [
            {
                "approval_id": "approval_1",
                "checkpoint_name": "pre_final_action",
                "reason": "High risk requires review.",
                "required_role": "senior_investigator",
                "status": "pending",
            }
        ],
    }

    patch = ApprovalCheckpointService().apply_decision(
        state,
        ApprovalDecisionRequest(
            approval_id="approval_1",
            reviewer_id="reviewer_1",
            decision="approved",
            rationale="Evidence supports escalation.",
        ),
    )
    latest = latest_approval_states([*state["approvals"], *patch["approvals"]])

    assert patch["status"] == "reporting"
    assert patch["next_route"] == "report_generation"
    assert latest["approval_1"]["status"] == "approved"
    assert latest["approval_1"]["reviewer_id"] == "reviewer_1"


def test_visualization_service_builds_timeline_from_state(
    high_risk_state: InvestigationState,
) -> None:
    state = {
        **high_risk_state,
        "status": "awaiting_human_approval",
        "workflow_history": [
            {
                "event_id": "evt_1",
                "node": "risk_router",
                "status": "routed",
                "message": "High risk routed to approval.",
                "created_at": "2026-05-20T10:00:00+00:00",
            },
            {
                "event_id": "evt_2",
                "node": "human_approval_checkpoint",
                "status": "interrupted",
                "message": "Workflow paused for approval.",
                "created_at": "2026-05-20T10:01:00+00:00",
            },
        ],
        "escalations": [
            {
                "escalation_id": "esc_1",
                "level": "senior_review",
                "reason": "High risk requires review.",
                "required_role": "senior_investigator",
                "created_at": "2026-05-20T10:00:30+00:00",
                "approval_id": "approval_1",
            }
        ],
    }

    metadata = WorkflowVisualizationService().build_metadata(state)

    assert metadata["workflow_id"] == state["thread_id"]
    assert metadata["case_id"] == state["case_id"]
    assert metadata["nodes"]
    assert metadata["edges"]
    assert metadata["edge_traversals"][0]["source"] == "risk_router"
    assert metadata["edge_traversals"][0]["target"] == "human_approval_checkpoint"
    assert metadata["escalations"][0]["escalation_level"] == "senior_review"
    assert [event["occurred_at"] for event in metadata["timeline"]] == sorted(
        event["occurred_at"] for event in metadata["timeline"]
    )
