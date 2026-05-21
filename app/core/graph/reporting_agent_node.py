from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.core.graph.retry import RetryPolicy, with_node_resilience
from app.core.graph.state import AgentExecution, ExecutiveReport, InvestigationState, WorkflowEvent
from app.services.reporting import ExecutiveReportingService

PartialState = dict[str, Any]


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


def _event(message: str) -> WorkflowEvent:
    return {
        "event_id": f"evt_{uuid4().hex}",
        "node": "reporting_agent",
        "status": "completed",
        "message": message,
        "created_at": _now(),
    }


def _agent_execution(report: ExecutiveReport) -> AgentExecution:
    return {
        "execution_id": f"exec_{uuid4().hex}",
        "agent_role": "report_writer",
        "node": "reporting_agent",
        "provider": "deterministic_reporting_service",
        "model": str(report["metadata"]["template_version"]) if report.get("metadata") else "v1",
        "started_at": _now(),
        "completed_at": _now(),
        "confidence": report["confidence"],
        "status": "success",
    }


async def reporting_agent_node(
    state: InvestigationState,
    *,
    service: ExecutiveReportingService | None = None,
) -> PartialState:
    """LangGraph-compatible executive reporting node."""

    reporting_service = service or ExecutiveReportingService()

    async def handler(current: InvestigationState) -> PartialState:
        report = await reporting_service.generate(current)
        return {
            "status": "closed" if report["status"] == "ready_for_review" else "reporting",
            "executive_report": report,
            "report_draft": reporting_service.render_markdown(report),
            "final_report_uri": (
                f"reports://investigations/{current['case_id']}/{report['report_id']}"
            ),
            "agent_executions": [_agent_execution(report)],
            "workflow_history": [_event("Executive report generated.")],
        }

    async def fallback(current: InvestigationState) -> PartialState:
        return {
            "status": "reporting",
            "report_draft": (
                f"Investigation {current['case_id']} requires manual report generation."
            ),
            "workflow_history": [_event("Reporting fallback used.")],
        }

    return await with_node_resilience(
        "reporting_agent",
        state,
        handler,
        fallback,
        policy=RetryPolicy(
            max_attempts=2,
            retry_route="human_approval_checkpoint",
            fallback_name="manual_review",
        ),
    )
