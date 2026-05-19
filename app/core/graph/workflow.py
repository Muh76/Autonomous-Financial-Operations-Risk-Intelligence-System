from typing import Any

from langgraph.graph import END, StateGraph

from app.core.graph.nodes import (
    collect_transaction_context_node,
    compliance_validation_node,
    critic_validation_node,
    escalation_router_node,
    evidence_expansion_node,
    fraud_analysis_node,
    human_approval_checkpoint_node,
    normalize_intake_node,
    report_generation_node,
    risk_scoring_node,
    workflow_failure_node,
)
from app.core.graph.state import InvestigationState, WorkflowRoute


WORKFLOW_VERSION = "financial-investigation-v1"
SCHEMA_VERSION = "investigation-state-v1"


def route_after_critic(state: InvestigationState) -> WorkflowRoute:
    return state.get("next_route", "report_generation")


def route_after_escalation(state: InvestigationState) -> WorkflowRoute:
    return state.get("next_route", "report_generation")


def build_investigation_workflow(
    *,
    checkpointer: Any | None = None,
    interrupt_before: list[str] | None = None,
) -> Any:
    """Build the durable financial investigation graph.

    A production deployment should pass a persistent LangGraph checkpointer, such as a
    Postgres-backed saver, and configure thread_id in the invocation config.
    """

    workflow = StateGraph(InvestigationState)

    workflow.add_node("normalize_intake", normalize_intake_node)
    workflow.add_node("collect_transaction_context", collect_transaction_context_node)
    workflow.add_node("fraud_analysis", fraud_analysis_node)
    workflow.add_node("compliance_validation", compliance_validation_node)
    workflow.add_node("risk_scoring", risk_scoring_node)
    workflow.add_node("critic_validation", critic_validation_node)
    workflow.add_node("evidence_expansion", evidence_expansion_node)
    workflow.add_node("escalation_router", escalation_router_node)
    workflow.add_node("human_approval_checkpoint", human_approval_checkpoint_node)
    workflow.add_node("report_generation", report_generation_node)
    workflow.add_node("workflow_failure", workflow_failure_node)

    workflow.set_entry_point("normalize_intake")
    workflow.add_edge("normalize_intake", "collect_transaction_context")
    workflow.add_edge("collect_transaction_context", "fraud_analysis")
    workflow.add_edge("fraud_analysis", "compliance_validation")
    workflow.add_edge("compliance_validation", "risk_scoring")
    workflow.add_edge("risk_scoring", "critic_validation")
    workflow.add_conditional_edges(
        "critic_validation",
        route_after_critic,
        {
            "report_generation": "report_generation",
            "evidence_expansion": "evidence_expansion",
            "escalation_router": "escalation_router",
            "workflow_failure": "workflow_failure",
            "human_approval_checkpoint": "human_approval_checkpoint",
        },
    )
    workflow.add_edge("evidence_expansion", "fraud_analysis")
    workflow.add_conditional_edges(
        "escalation_router",
        route_after_escalation,
        {
            "report_generation": "report_generation",
            "human_approval_checkpoint": "human_approval_checkpoint",
            "workflow_failure": "workflow_failure",
            "evidence_expansion": "evidence_expansion",
            "escalation_router": "escalation_router",
        },
    )
    workflow.add_edge("human_approval_checkpoint", END)
    workflow.add_edge("report_generation", END)
    workflow.add_edge("workflow_failure", END)

    compile_options: dict[str, Any] = {}
    if checkpointer is not None:
        compile_options["checkpointer"] = checkpointer
    if interrupt_before is not None:
        compile_options["interrupt_before"] = interrupt_before

    return workflow.compile(**compile_options)


async def run_investigation_workflow(
    transaction_id: str,
    *,
    tenant_id: str = "default",
    transaction_amount: float = 0.0,
    transaction_currency: str = "USD",
    jurisdiction: str = "US",
    checkpointer: Any | None = None,
) -> InvestigationState:
    workflow = build_investigation_workflow(checkpointer=checkpointer)
    thread_id = f"thread_{tenant_id}_{transaction_id}"
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
    config = {"configurable": {"thread_id": thread_id}}
    return await workflow.ainvoke(initial_state, config=config)
