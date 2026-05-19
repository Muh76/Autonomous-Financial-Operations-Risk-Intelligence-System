from typing import NotRequired, TypedDict

from app.core.graph.state_schemas.enums import EvidenceType, FindingCategory, RiskBand


class EvidenceRef(TypedDict):
    """Reference to evidence stored outside graph state."""

    evidence_id: str
    evidence_type: EvidenceType
    source_system: str
    uri: str
    collected_at: str
    summary: str
    content_hash: NotRequired[str]
    retention_policy: NotRequired[str]


class InvestigationFinding(TypedDict):
    """Typed, provenance-aware investigation finding."""

    finding_id: str
    category: FindingCategory
    severity: RiskBand
    description: str
    evidence_ids: list[str]
    confidence: float
    source_node: str
    policy_refs: NotRequired[list[str]]
    model_refs: NotRequired[list[str]]
