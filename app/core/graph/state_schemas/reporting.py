from typing import Literal, NotRequired, TypedDict


ReportAudience = Literal["executive", "audit", "compliance", "operations"]


class ReportCitation(TypedDict):
    """Citation used in executive and audit reporting."""

    citation_id: str
    title: str
    source_uri: str
    attribution: str
    quote: str


class ReportFinding(TypedDict):
    """Evidence-backed report finding."""

    finding_id: str
    severity: Literal["low", "medium", "high", "critical"]
    title: str
    summary: str
    evidence_ids: list[str]
    citation_ids: list[str]
    confidence: float


class ReportSection(TypedDict):
    """Structured report section for rendering and export."""

    section_id: str
    heading: str
    content: str
    citations: list[ReportCitation]
    confidence: float


class ExecutiveReport(TypedDict):
    """Typed executive reporting output."""

    report_id: str
    case_id: str
    transaction_id: str
    audience: ReportAudience
    title: str
    executive_summary: str
    investigation_summary: str
    risk_summary: str
    escalation_summary: str
    audit_explanation: str
    evidence_summary: str
    findings: list[ReportFinding]
    sections: list[ReportSection]
    citations: list[ReportCitation]
    confidence: float
    status: Literal["draft", "ready_for_review", "final"]
    recommended_actions: list[str]
    generated_at: str
    metadata: NotRequired[dict[str, str | int | float | bool | None]]
