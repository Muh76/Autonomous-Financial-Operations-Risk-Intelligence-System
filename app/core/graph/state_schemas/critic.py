from typing import Literal, NotRequired, TypedDict


CriticFindingType = Literal[
    "hallucination",
    "unsupported_claim",
    "evidence_mismatch",
    "contradiction",
    "reasoning_inconsistency",
    "confidence_miscalibration",
    "missing_citation",
]


class CriticFinding(TypedDict):
    """One explainable reliability finding emitted by the Critic Agent."""

    finding_id: str
    finding_type: CriticFindingType
    severity: Literal["low", "medium", "high", "critical"]
    target_agent: str
    claim: str
    explanation: str
    evidence_refs: list[str]
    recommendation: str
    confidence: float


class EvidenceVerificationResult(TypedDict):
    """Evidence-grounding result for one target agent output."""

    target_agent: str
    checked_claims: int
    supported_claims: int
    unsupported_claims: int
    citation_count: int
    grounding_score: float


class ContradictionResult(TypedDict):
    """Contradiction result comparing outputs across agents."""

    contradiction_id: str
    left_agent: str
    right_agent: str
    description: str
    severity: Literal["low", "medium", "high", "critical"]
    evidence_refs: list[str]


class ConfidenceCalibrationResult(TypedDict):
    """Confidence calibration assessment for agent outputs."""

    target_agent: str
    reported_confidence: float
    evidence_confidence: float
    calibrated_confidence: float
    calibration_delta: float
    status: Literal["aligned", "overconfident", "underconfident"]


class CriticValidationResult(TypedDict):
    """Typed response schema for enterprise AI reliability validation."""

    passed: bool
    reliability_score: float
    confidence: float
    findings: list[CriticFinding]
    evidence_verification: list[EvidenceVerificationResult]
    contradictions: list[ContradictionResult]
    confidence_calibration: list[ConfidenceCalibrationResult]
    safety_recommendation: Literal[
        "continue",
        "revise_outputs",
        "expand_evidence",
        "human_review",
        "block_final_action",
    ]
    summary: str
    required_actions: list[str]
    policy_version: str
    model_version: str
    metadata: NotRequired[dict[str, str | int | float | bool | None]]
