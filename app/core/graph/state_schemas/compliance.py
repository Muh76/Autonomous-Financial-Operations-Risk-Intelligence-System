from typing import Literal, NotRequired, TypedDict


ComplianceRuleCategory = Literal[
    "kyc",
    "aml",
    "sanctions",
    "threshold",
    "policy",
    "suspicious_activity",
]


class ComplianceRuleResult(TypedDict):
    """One explainable rule result from the Compliance Agent."""

    rule_id: str
    category: ComplianceRuleCategory
    passed: bool
    severity: Literal["low", "medium", "high", "critical"]
    rationale: str
    policy_refs: list[str]
    evidence_refs: list[str]
    confidence: float


class ComplianceCitation(TypedDict):
    """Policy citation used to ground compliance reasoning."""

    citation_id: str
    title: str
    source_uri: str
    quote: str
    attribution: str


class ComplianceRecommendation(TypedDict):
    """Compliance escalation or continuation recommendation."""

    level: Literal["none", "analyst_review", "compliance_review", "regulatory", "block"]
    required_role: str
    rationale: str
    recommended_actions: list[str]


class ComplianceValidationResult(TypedDict):
    """Typed response schema for rule-based compliance automation."""

    passed: bool
    compliance_score: float
    confidence: float
    flags: list[str]
    rule_results: list[ComplianceRuleResult]
    citations: list[ComplianceCitation]
    recommendation: ComplianceRecommendation
    suspicious_activity_summary: str
    policy_version: str
    reasoning: str
    metadata: NotRequired[dict[str, str | int | float | bool | None]]
