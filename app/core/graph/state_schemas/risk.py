from typing import NotRequired, TypedDict

from app.core.graph.state_schemas.enums import EscalationLevel, RiskBand


class RiskSignalScore(TypedDict):
    """One explainable weighted input into operational risk scoring."""

    signal_name: str
    raw_score: float
    weight: float
    weighted_score: float
    confidence: float
    rationale: str


class EscalationRecommendation(TypedDict):
    """Prioritized escalation recommendation with operational rationale."""

    level: EscalationLevel
    priority: int
    required_role: str
    rationale: str
    recommended_actions: list[str]


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


class OperationalRiskScore(TypedDict):
    """Production scoring response for explainable operational risk workflows."""

    aggregate_score: float
    severity_score: float
    risk_band: RiskBand
    confidence: float
    signals: list[RiskSignalScore]
    escalation: EscalationRecommendation
    critic_adjustments: list[str]
    evidence_gaps: list[str]
    recommended_actions: list[str]
    explanation: str
    policy_version: str
    scoring_model_version: str
