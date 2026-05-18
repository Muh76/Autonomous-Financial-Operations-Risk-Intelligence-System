from typing import Any

from langgraph.graph import END, StateGraph

from app.core.graph.nodes import transaction_analysis_node
from app.core.graph.state import InvestigationState


def build_investigation_workflow() -> Any:
    workflow = StateGraph(InvestigationState)
    workflow.add_node("transaction_analysis", transaction_analysis_node)
    workflow.set_entry_point("transaction_analysis")
    workflow.add_edge("transaction_analysis", END)
    return workflow.compile()


async def run_investigation_workflow(transaction_id: str) -> InvestigationState:
    workflow = build_investigation_workflow()
    initial_state: InvestigationState = {
        "transaction_id": transaction_id,
        "findings": [],
        "workflow_history": [],
    }
    return await workflow.ainvoke(initial_state)
