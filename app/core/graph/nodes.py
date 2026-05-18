from app.core.graph.state import EscalationLevel, InvestigationState


def _escalation_from_score(risk_score: int) -> EscalationLevel:
    if risk_score >= 90:
        return "block"
    if risk_score >= 70:
        return "escalate"
    if risk_score >= 40:
        return "review"
    return "none"


async def transaction_analysis_node(state: InvestigationState) -> InvestigationState:
    transaction_id = state["transaction_id"].strip()
    if not transaction_id:
        raise ValueError("transaction_id is required for investigation workflow execution")

    existing_findings = state.get("findings", [])
    evidence_available = len(existing_findings) > 0
    risk_score = 45 if evidence_available else 35
    escalation_level = _escalation_from_score(risk_score)

    findings = [
        (
            "Transaction accepted for investigation; existing evidence will be used for initial "
            "risk triage."
            if evidence_available
            else "Transaction accepted for investigation; no prior evidence was attached at intake."
        )
    ]

    return {
        "transaction_id": transaction_id,
        "findings": findings,
        "risk_score": risk_score,
        "escalation_level": escalation_level,
        "workflow_history": ["transaction_analysis_node"],
    }
