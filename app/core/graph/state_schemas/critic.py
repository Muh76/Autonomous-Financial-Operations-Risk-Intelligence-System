from typing import Literal, NotRequired, TypedDict


CriticFindingType = Literal[
    "hallucination",
    "unsupported_claim",
    "evidence_mismatch",
    "contradiction",
    "reasoning_inconsistency",
    "confidence_miscalibration",
    "missing_citation",
    "invalid_citation",
    "retrieval_grounding_gap",
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


class CitationValidationResult(TypedDict):
    """Citation integrity result for generated or retrieved outputs."""

    target_agent: str
    checked_citations: int
    valid_citations: int
    invalid_citations: int
    missing_citations: int
    citation_support_score: float


class RetrievalGroundingResult(TypedDict):
    """Retrieval grounding assessment for evidence-backed claims."""

    target_agent: str
    grounded_claims: int
    ungrounded_claims: int
    retrieval_evidence_count: int
    retrieval_citation_count: int
    grounding_status: Literal["grounded", "partial", "ungrounded"]


class ReasoningConsistencyResult(TypedDict):
    """Reasoning consistency validation across outputs and decisions."""

    target_agent: str
    checked_rules: int
    passed_rules: int
    failed_rules: int
    consistency_score: float
    notes: list[str]


class ReliabilityScoreBreakdown(TypedDict):
    """Explainable reliability scoring components."""

    grounding_score: float
    citation_support_score: float
    contradiction_score: float
    confidence_calibration_score: float
    reasoning_consistency_score: float
    finding_penalty: float


class CriticValidationResult(TypedDict):
    """Typed response schema for enterprise AI reliability validation."""

    passed: bool
    reliability_score: float
    confidence: float
    findings: list[CriticFinding]
    evidence_verification: list[EvidenceVerificationResult]
    contradictions: list[ContradictionResult]
    confidence_calibration: list[ConfidenceCalibrationResult]
    citation_validation: list[CitationValidationResult]
    retrieval_grounding: list[RetrievalGroundingResult]
    reasoning_consistency: list[ReasoningConsistencyResult]
    score_breakdown: ReliabilityScoreBreakdown
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
