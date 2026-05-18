from langgraph.graph import END, StateGraph

from app.agents.state import FinancialOperationState


async def enrich_context(state: FinancialOperationState) -> FinancialOperationState:
    findings = [*state.get("findings", []), "Context enrichment placeholder completed."]
    return {**state, "findings": findings}


async def assess_risk(state: FinancialOperationState) -> FinancialOperationState:
    amount = state.get("amount") or 0
    risk_level = "high" if amount >= 100_000 else "medium" if amount >= 10_000 else "low"
    findings = [*state.get("findings", []), f"Risk level classified as {risk_level}."]
    return {**state, "risk_level": risk_level, "findings": findings}


async def recommend_actions(state: FinancialOperationState) -> FinancialOperationState:
    risk_level = state.get("risk_level", "low")
    actions = {
        "low": ["Auto-approve with standard audit log."],
        "medium": ["Queue for policy review."],
        "high": ["Require manager approval and enhanced monitoring."],
        "critical": ["Block operation and escalate to risk team."],
    }
    return {**state, "recommended_actions": actions[risk_level]}


def build_financial_operations_graph():
    graph = StateGraph(FinancialOperationState)
    graph.add_node("enrich_context", enrich_context)
    graph.add_node("assess_risk", assess_risk)
    graph.add_node("recommend_actions", recommend_actions)
    graph.set_entry_point("enrich_context")
    graph.add_edge("enrich_context", "assess_risk")
    graph.add_edge("assess_risk", "recommend_actions")
    graph.add_edge("recommend_actions", END)
    return graph.compile()
