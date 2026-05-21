from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from app.core.graph.state import InvestigationState
from app.core.graph.state_schemas import (
    ExecutiveReport,
    ReportCitation,
    ReportFinding,
    ReportSection,
)


def _now() -> str:
    return datetime.now(tz=UTC).isoformat()


@dataclass(frozen=True)
class ReportingPolicy:
    min_ready_confidence: float = 0.65
    report_template_version: str = "executive-report-template-v1"


class ExecutiveReportingService:
    """Structured, citation-aware executive reporting service."""

    def __init__(self, policy: ReportingPolicy | None = None) -> None:
        self._policy = policy or ReportingPolicy()

    async def generate(self, state: InvestigationState) -> ExecutiveReport:
        citations = self._citations(state)
        findings = self._findings(state, citations)
        confidence = self._confidence(state, findings, citations)
        sections = self._sections(state, citations, confidence)
        status = "ready_for_review" if confidence >= self._policy.min_ready_confidence else "draft"

        return {
            "report_id": f"report_{uuid4().hex}",
            "case_id": state["case_id"],
            "transaction_id": state["transaction_id"],
            "audience": "executive",
            "title": f"Executive Investigation Report: {state['case_id']}",
            "executive_summary": self._executive_summary(state),
            "investigation_summary": self._investigation_summary(state),
            "risk_summary": self._risk_summary(state),
            "escalation_summary": self._escalation_summary(state),
            "audit_explanation": self._audit_explanation(state),
            "evidence_summary": self._evidence_summary(state, citations),
            "findings": findings,
            "sections": sections,
            "citations": citations,
            "confidence": confidence,
            "status": status,
            "recommended_actions": self._recommended_actions(state),
            "generated_at": _now(),
            "metadata": {
                "template_version": self._policy.report_template_version,
                "citation_count": len(citations),
                "finding_count": len(findings),
            },
        }

    def render_markdown(self, report: ExecutiveReport) -> str:
        lines = [
            f"# {report['title']}",
            "",
            f"Status: {report['status']}",
            f"Confidence: {report['confidence']}",
            "",
            "## Executive Summary",
            report["executive_summary"],
            "",
            "## Risk Summary",
            report["risk_summary"],
            "",
            "## Escalation Summary",
            report["escalation_summary"],
            "",
            "## Evidence-Backed Findings",
        ]
        for finding in report["findings"]:
            citations = ", ".join(finding["citation_ids"]) or "none"
            lines.extend(
                [
                    f"- {finding['severity'].upper()}: {finding['title']}",
                    f"  {finding['summary']}",
                    f"  Citations: {citations}",
                ]
            )
        lines.extend(["", "## Audit Explanation", report["audit_explanation"], ""])
        if report["citations"]:
            lines.append("## Citations")
            for citation in report["citations"]:
                lines.append(f"- [{citation['citation_id']}] {citation['attribution']}")
        return "\n".join(lines)

    def _citations(self, state: InvestigationState) -> list[ReportCitation]:
        citations: list[ReportCitation] = []
        seen: set[str] = set()
        for citation in state.get("financial_retrieval", {}).get("citations", []):
            citation_id = citation["citation_id"]
            if citation_id in seen:
                continue
            seen.add(citation_id)
            citations.append(
                {
                    "citation_id": citation_id,
                    "title": citation["title"],
                    "source_uri": citation["source_uri"],
                    "attribution": citation["attribution"],
                    "quote": citation["quote"],
                }
            )
        for citation in state.get("compliance_validation", {}).get("citations", []):
            citation_id = citation["citation_id"]
            if citation_id in seen:
                continue
            seen.add(citation_id)
            citations.append(
                {
                    "citation_id": citation_id,
                    "title": citation["title"],
                    "source_uri": citation["source_uri"],
                    "attribution": citation["attribution"],
                    "quote": citation["quote"],
                }
            )
        return citations

    def _findings(
        self,
        state: InvestigationState,
        citations: list[ReportCitation],
    ) -> list[ReportFinding]:
        citation_ids = [citation["citation_id"] for citation in citations]
        findings: list[ReportFinding] = []
        if state.get("fraud_detection"):
            fraud = state["fraud_detection"]
            findings.append(
                self._finding(
                    "Fraud Detection",
                    fraud["risk_band"],
                    fraud["explanation"],
                    [item["evidence_id"] for item in state.get("evidence", [])],
                    citation_ids,
                    fraud["confidence"],
                )
            )
        if state.get("compliance_validation"):
            compliance = state["compliance_validation"]
            severity = "high" if compliance["flags"] else "low"
            findings.append(
                self._finding(
                    "Compliance Review",
                    severity,
                    compliance["reasoning"],
                    [item["evidence_id"] for item in state.get("evidence", [])],
                    citation_ids,
                    compliance["confidence"],
                )
            )
        if state.get("operational_risk"):
            risk = state["operational_risk"]
            findings.append(
                self._finding(
                    "Operational Risk",
                    risk["risk_band"],
                    risk["explanation"],
                    [item["evidence_id"] for item in state.get("evidence", [])],
                    citation_ids,
                    risk["confidence"],
                )
            )
        if state.get("critic_validation"):
            critic = state["critic_validation"]
            severity = "low" if critic["passed"] else "high"
            findings.append(
                self._finding(
                    "Critic Validation",
                    severity,
                    critic["summary"],
                    [item["evidence_id"] for item in state.get("evidence", [])],
                    citation_ids,
                    critic["confidence"],
                )
            )
        return findings

    def _finding(
        self,
        title: str,
        severity: str,
        summary: str,
        evidence_ids: list[str],
        citation_ids: list[str],
        confidence: float,
    ) -> ReportFinding:
        return {
            "finding_id": f"report_finding_{uuid4().hex}",
            "severity": severity,
            "title": title,
            "summary": summary,
            "evidence_ids": evidence_ids,
            "citation_ids": citation_ids,
            "confidence": confidence,
        }

    def _sections(
        self,
        state: InvestigationState,
        citations: list[ReportCitation],
        confidence: float,
    ) -> list[ReportSection]:
        return [
            self._section(
                "executive_summary",
                "Executive Summary",
                self._executive_summary(state),
                citations,
                confidence,
            ),
            self._section(
                "risk_summary",
                "Risk Summary",
                self._risk_summary(state),
                citations,
                confidence,
            ),
            self._section(
                "audit_explanation",
                "Audit Explanation",
                self._audit_explanation(state),
                citations,
                confidence,
            ),
        ]

    def _section(
        self,
        section_id: str,
        heading: str,
        content: str,
        citations: list[ReportCitation],
        confidence: float,
    ) -> ReportSection:
        return {
            "section_id": section_id,
            "heading": heading,
            "content": content,
            "citations": citations,
            "confidence": confidence,
        }

    def _executive_summary(self, state: InvestigationState) -> str:
        risk_band = state.get("risk_band") or state.get("operational_risk", {}).get(
            "risk_band",
            "unknown",
        )
        escalation = state.get("escalation_level") or state.get("operational_risk", {}).get(
            "escalation",
            {},
        ).get("level", "none")
        return (
            f"Investigation {state['case_id']} for transaction {state['transaction_id']} "
            f"is assessed as {risk_band} risk with escalation level {escalation}."
        )

    def _investigation_summary(self, state: InvestigationState) -> str:
        return (
            f"The investigation reviewed fraud, compliance, retrieval, risk scoring, "
            f"and critic validation outputs for transaction {state['transaction_id']}."
        )

    def _risk_summary(self, state: InvestigationState) -> str:
        if state.get("operational_risk"):
            risk = state["operational_risk"]
            return (
                f"Operational risk score is {risk['severity_score']} with confidence "
                f"{risk['confidence']}. {risk['explanation']}"
            )
        return f"Aggregate risk score is {state.get('aggregate_risk_score', 'unavailable')}."

    def _escalation_summary(self, state: InvestigationState) -> str:
        if state.get("operational_risk"):
            escalation = state["operational_risk"]["escalation"]
            return f"{escalation['level']} escalation recommended: {escalation['rationale']}"
        if state.get("escalations"):
            return f"{len(state['escalations'])} escalation records are attached."
        return "No escalation has been recommended."

    def _audit_explanation(self, state: InvestigationState) -> str:
        critic = state.get("critic_validation")
        if critic:
            return (
                f"Critic validation passed={critic['passed']} with reliability score "
                f"{critic['reliability_score']} and recommendation "
                f"{critic['safety_recommendation']}."
            )
        return "Audit explanation is based on structured workflow evidence and agent outputs."

    def _evidence_summary(self, state: InvestigationState, citations: list[ReportCitation]) -> str:
        return (
            f"{len(state.get('evidence', []))} workflow evidence references and "
            f"{len(citations)} citations support this report."
        )

    def _recommended_actions(self, state: InvestigationState) -> list[str]:
        actions = list(state.get("recommended_actions", []))
        if state.get("operational_risk"):
            actions.extend(state["operational_risk"]["recommended_actions"])
        if state.get("critic_validation"):
            actions.extend(state["critic_validation"]["required_actions"])
        return list(dict.fromkeys(actions)) or ["archive_report"]

    def _confidence(
        self,
        state: InvestigationState,
        findings: list[ReportFinding],
        citations: list[ReportCitation],
    ) -> float:
        if not findings:
            return 0.0
        avg = sum(finding["confidence"] for finding in findings) / len(findings)
        citation_bonus = min(0.12, len(citations) * 0.03)
        critic_bonus = 0.08 if state.get("critic_validation", {}).get("passed") else 0.0
        return round(min(0.97, avg * 0.82 + citation_bonus + critic_bonus), 2)
