from typing import Any

from langgraph.graph import END, StateGraph

from app.core.graph.state import RiskWorkflowState


async def classify_risk(state: RiskWorkflowState) -> RiskWorkflowState:
    risk_level = "high" if state["amount"] >= 100_000 else "medium" if state["amount"] >= 10_000 else "low"
    return {**state, "risk_level": risk_level}


async def decide_action(state: RiskWorkflowState) -> RiskWorkflowState:
    decisions = {
        "low": "approve",
        "medium": "review",
        "high": "escalate",
        "critical": "block",
    }
    risk_level = state["risk_level"]
    if risk_level is None:
        raise ValueError("risk_level must be set before deciding an action")
    return {**state, "decision": decisions[risk_level]}


def build_risk_workflow() -> Any:
    workflow = StateGraph(RiskWorkflowState)
    workflow.add_node("classify_risk", classify_risk)
    workflow.add_node("decide_action", decide_action)
    workflow.set_entry_point("classify_risk")
    workflow.add_edge("classify_risk", "decide_action")
    workflow.add_edge("decide_action", END)
    return workflow.compile()
