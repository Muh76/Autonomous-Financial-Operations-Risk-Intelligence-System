from datetime import datetime
from typing import Any
from uuid import uuid4

from app.core.graph.state import InvestigationState
from app.core.graph.state_schemas import (
    EdgeTraversalTrace,
    EscalationPathTrace,
    GraphEdgeMetadata,
    GraphNodeMetadata,
    NodeExecutionTrace,
    RetryVisualizationTrace,
    WorkflowTimelineEvent,
    WorkflowVisualizationMetadata,
)


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _duration_ms(started_at: str | None, completed_at: str | None) -> int | None:
    started = _parse_time(started_at)
    completed = _parse_time(completed_at)
    if started is None or completed is None:
        return None
    return max(0, round((completed - started).total_seconds() * 1000))


def _timeline_event(
    *,
    event_type: str,
    label: str,
    occurred_at: str,
    node_id: str | None = None,
    severity: str | None = None,
    summary: str | None = None,
    metadata: dict[str, str | int | float | bool | None] | None = None,
) -> WorkflowTimelineEvent:
    event: WorkflowTimelineEvent = {
        "event_id": f"timeline_{uuid4().hex}",
        "event_type": event_type,
        "label": label,
        "occurred_at": occurred_at,
    }
    if node_id is not None:
        event["node_id"] = node_id
    if severity is not None:
        event["severity"] = severity
    if summary is not None:
        event["summary"] = summary
    if metadata is not None:
        event["metadata"] = metadata
    return event


def default_investigation_graph_metadata() -> tuple[
    list[GraphNodeMetadata],
    list[GraphEdgeMetadata],
]:
    """Return static metadata for the default investigation graph."""

    nodes: list[GraphNodeMetadata] = [
        {
            "node_id": "normalize_intake",
            "label": "Normalize Intake",
            "node_type": "coordination",
            "group": "intake",
        },
        {
            "node_id": "collect_transaction_context",
            "label": "Collect Transaction Context",
            "node_type": "agent",
            "agent_role": "transaction_investigator",
            "group": "enrichment",
            "retryable": True,
        },
        {
            "node_id": "fraud_analysis",
            "label": "Fraud Analysis",
            "node_type": "agent",
            "agent_role": "fraud_analyst",
            "group": "analysis",
            "retryable": True,
        },
        {
            "node_id": "compliance_validation",
            "label": "Compliance Validation",
            "node_type": "agent",
            "agent_role": "compliance_reviewer",
            "group": "analysis",
            "retryable": True,
        },
        {
            "node_id": "risk_scoring",
            "label": "Risk Scoring",
            "node_type": "deterministic",
            "agent_role": "risk_scorer",
            "group": "decisioning",
        },
        {
            "node_id": "risk_router",
            "label": "Risk Router",
            "node_type": "router",
            "group": "decisioning",
        },
        {
            "node_id": "critic_validation",
            "label": "Critic Validation",
            "node_type": "agent",
            "agent_role": "critic",
            "group": "quality",
        },
        {
            "node_id": "evidence_expansion",
            "label": "Evidence Expansion",
            "node_type": "agent",
            "group": "enrichment",
            "retryable": True,
        },
        {
            "node_id": "escalation_router",
            "label": "Escalation Router",
            "node_type": "router",
            "group": "escalation",
        },
        {
            "node_id": "human_approval_checkpoint",
            "label": "Human Approval",
            "node_type": "checkpoint",
            "requires_human": True,
            "group": "escalation",
        },
        {
            "node_id": "report_generation",
            "label": "Report Generation",
            "node_type": "agent",
            "agent_role": "report_writer",
            "group": "closure",
        },
        {
            "node_id": "workflow_failure",
            "label": "Workflow Failure",
            "node_type": "terminal",
            "group": "closure",
        },
    ]
    edges: list[GraphEdgeMetadata] = [
        _edge("normalize_intake", "collect_transaction_context"),
        _edge("collect_transaction_context", "fraud_analysis"),
        _edge("fraud_analysis", "compliance_validation"),
        _edge("compliance_validation", "risk_scoring"),
        _edge("risk_scoring", "risk_router"),
        _edge("risk_router", "low_risk_auto_close", condition="low risk"),
        _edge("risk_router", "medium_risk_compliance_review", condition="medium risk"),
        _edge("risk_router", "escalation_router", condition="high risk"),
        _edge("critic_validation", "report_generation", condition="critic passed"),
        _edge("critic_validation", "evidence_expansion", condition="critic failed"),
        _edge("escalation_router", "human_approval_checkpoint", condition="approval required"),
        _edge("escalation_router", "report_generation", condition="approval not required"),
        _edge("human_approval_checkpoint", "report_generation", condition="approved"),
        _edge("human_approval_checkpoint", "evidence_expansion", condition="rejected"),
    ]
    return nodes, edges


def _edge(source: str, target: str, *, condition: str | None = None) -> GraphEdgeMetadata:
    edge: GraphEdgeMetadata = {
        "edge_id": f"{source}->{target}",
        "source": source,
        "target": target,
        "edge_type": "conditional" if condition else "normal",
    }
    if condition is not None:
        edge["condition"] = condition
        edge["label"] = condition
    return edge


class WorkflowVisualizationService:
    """Build dashboard-ready workflow traces from LangGraph investigation state."""

    def build_metadata(self, state: InvestigationState) -> WorkflowVisualizationMetadata:
        nodes, edges = default_investigation_graph_metadata()
        node_traces = self.build_node_traces(state)
        edge_traversals = self.build_edge_traversals(state)
        retries = self.build_retry_traces(state)
        escalations = self.build_escalation_traces(state)
        timeline = self.build_timeline(
            state,
            node_traces=node_traces,
            edge_traversals=edge_traversals,
            retries=retries,
            escalations=escalations,
        )
        return {
            "workflow_id": state["thread_id"],
            "case_id": state["case_id"],
            "tenant_id": state["tenant_id"],
            "status": state["status"],
            "nodes": nodes,
            "edges": edges,
            "node_traces": node_traces,
            "edge_traversals": edge_traversals,
            "retries": retries,
            "escalations": escalations,
            "timeline": timeline,
        }

    def build_node_traces(self, state: InvestigationState) -> list[NodeExecutionTrace]:
        traces = list(state.get("node_traces", []))
        traced_nodes = {trace["node_id"] for trace in traces}
        for execution in state.get("agent_executions", []):
            node_id = execution["node"]
            if node_id in traced_nodes:
                continue
            trace: NodeExecutionTrace = {
                "trace_id": execution["execution_id"],
                "node_id": node_id,
                "status": execution["status"],
                "started_at": execution["started_at"],
                "attempt": 1,
            }
            completed_at = execution.get("completed_at")
            if completed_at is not None:
                trace["completed_at"] = completed_at
            duration = execution.get("latency_ms") or _duration_ms(
                execution["started_at"],
                completed_at,
            )
            if duration is not None:
                trace["duration_ms"] = duration
            if "confidence" in execution:
                trace["confidence"] = execution["confidence"]
            traces.append(trace)
            traced_nodes.add(node_id)

        for result in state.get("node_results", []):
            node_id = result["node"]
            if node_id in traced_nodes:
                continue
            trace = {
                "trace_id": f"trace_{uuid4().hex}",
                "node_id": node_id,
                "status": result["status"],
                "started_at": result["created_at"],
                "completed_at": result["created_at"],
                "duration_ms": 0,
                "attempt": 1,
                "output_fields": result["output_fields"],
            }
            if "confidence" in result:
                trace["confidence"] = result["confidence"]
            if "error" in result:
                trace["error_type"] = result["error"]["error_type"]
                trace["error_message"] = result["error"]["message"]
            traces.append(trace)
            traced_nodes.add(node_id)
        return traces

    def build_edge_traversals(self, state: InvestigationState) -> list[EdgeTraversalTrace]:
        traversals = list(state.get("edge_traversals", []))
        events = sorted(
            state.get("workflow_history", []),
            key=lambda event: event["created_at"],
        )
        for previous, current in zip(events, events[1:]):
            if previous["node"] == current["node"]:
                continue
            traversals.append(
                {
                    "traversal_id": f"edge_{uuid4().hex}",
                    "source": previous["node"],
                    "target": current["node"],
                    "traversed_at": current["created_at"],
                    "route": previous.get("route"),
                    "reason": current["message"],
                }
            )
        return traversals

    def build_retry_traces(self, state: InvestigationState) -> list[RetryVisualizationTrace]:
        traces: list[RetryVisualizationTrace] = []
        for retry in state.get("retry_state", {}).values():
            traces.append(
                {
                    "retry_id": f"retry_{retry['node']}_{retry['attempts']}",
                    "node_id": retry["node"],
                    "attempt": retry["attempts"],
                    "max_attempts": retry["max_attempts"],
                    "retryable": retry["retryable"],
                    "failure_class": retry.get("last_failure_class"),
                    "fallback_used": retry.get("fallback_used"),
                    "next_retry_route": retry.get("next_retry_route"),
                }
            )
        return traces

    def build_escalation_traces(self, state: InvestigationState) -> list[EscalationPathTrace]:
        traces: list[EscalationPathTrace] = []
        for escalation in state.get("escalations", []):
            traces.append(
                {
                    "escalation_id": escalation["escalation_id"],
                    "source_node": "escalation_router",
                    "escalation_level": escalation["level"],
                    "required_role": escalation["required_role"],
                    "reason": escalation["reason"],
                    "created_at": escalation["created_at"],
                    "approval_id": escalation.get("approval_id"),
                    "resolved_at": escalation.get("resolved_at"),
                }
            )
        return traces

    def build_timeline(
        self,
        state: InvestigationState,
        *,
        node_traces: list[NodeExecutionTrace],
        edge_traversals: list[EdgeTraversalTrace],
        retries: list[RetryVisualizationTrace],
        escalations: list[EscalationPathTrace],
    ) -> list[WorkflowTimelineEvent]:
        timeline = list(state.get("timeline_events", []))
        for event in state.get("workflow_history", []):
            event_type = "node_completed"
            if event["status"] == "failed":
                event_type = "node_failed"
            elif event["status"] == "interrupted":
                event_type = "workflow_paused"
            elif event["status"] == "fallback":
                event_type = "fallback_used"
            timeline.append(
                _timeline_event(
                    event_type=event_type,
                    label=event["node"],
                    occurred_at=event["created_at"],
                    node_id=event["node"],
                    severity=event["status"],
                    summary=event["message"],
                )
            )

        for trace in node_traces:
            if "completed_at" not in trace:
                continue
            timeline.append(
                _timeline_event(
                    event_type="node_completed",
                    label=f"{trace['node_id']} completed",
                    occurred_at=trace["completed_at"],
                    node_id=trace["node_id"],
                    severity=trace["status"],
                    metadata={"duration_ms": trace.get("duration_ms")},
                )
            )

        for traversal in edge_traversals:
            timeline.append(
                _timeline_event(
                    event_type="edge_traversed",
                    label=f"{traversal['source']} -> {traversal['target']}",
                    occurred_at=traversal["traversed_at"],
                    summary=traversal.get("reason"),
                )
            )

        for retry in retries:
            timeline.append(
                _timeline_event(
                    event_type="retry_scheduled",
                    label=f"Retry {retry['node_id']}",
                    occurred_at=state.get("workflow_history", [{}])[-1].get("created_at", ""),
                    node_id=retry["node_id"],
                    severity=retry.get("failure_class"),
                    metadata={
                        "attempt": retry["attempt"],
                        "max_attempts": retry["max_attempts"],
                    },
                )
            )

        for escalation in escalations:
            timeline.append(
                _timeline_event(
                    event_type="escalation_requested",
                    label=f"{escalation['escalation_level']} escalation",
                    occurred_at=escalation["created_at"],
                    node_id=escalation["source_node"],
                    severity=escalation["escalation_level"],
                    summary=escalation["reason"],
                )
            )

        return sorted(timeline, key=lambda event: event["occurred_at"])
