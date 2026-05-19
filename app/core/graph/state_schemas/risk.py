from typing import NotRequired, TypedDict

from app.core.graph.state_schemas.enums import EscalationLevel, RiskBand


class RiskAssessment(TypedDict):
    """Structured risk assessment for transaction, compliance, and aggregate scoring."""

    fraud_score: float
    compliance_score: float
    transaction_score: float
    customer_score: float
    aggregate_score: float
    risk_band: RiskBand
    escalation_level: EscalationLevel
    scoring_model_version: str
    policy_version: str
    confidence: float
    recommended_actions: list[str]
    score_components: NotRequired[dict[str, float]]
    explanation: NotRequired[str]
