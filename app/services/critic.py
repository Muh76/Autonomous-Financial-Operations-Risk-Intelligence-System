from dataclasses import dataclass
from uuid import uuid4

from app.core.graph.state import InvestigationState
from app.core.graph.state_schemas import (
    CitationValidationResult,
    ConfidenceCalibrationResult,
    ContradictionResult,
    CriticFinding,
    CriticValidationResult,
    EvidenceVerificationResult,
    ReasoningConsistencyResult,
    ReliabilityScoreBreakdown,
    RetrievalGroundingResult,
)


@dataclass(frozen=True)
class CriticPolicy:
    min_reliability_score: float = 0.72
    high_confidence_threshold: float = 0.85
    min_citation_count_for_high_risk: int = 1
    min_report_citation_support: float = 0.8
    min_retrieval_grounding_score: float = 0.7
    policy_version: str = "enterprise-critic-policy-v1"
    model_version: str = "deterministic-critic-v1"


class CriticService:
    """Enterprise reliability critic for grounded AI workflow outputs."""

    def __init__(self, policy: CriticPolicy | None = None) -> None:
        self._policy = policy or CriticPolicy()

    async def validate(self, state: InvestigationState) -> CriticValidationResult:
        evidence_verification = self._verify_evidence(state)
        citation_validation = self._validate_citations(state)
        retrieval_grounding = self._check_retrieval_grounding(state)
        contradictions = self._detect_contradictions(state)
        calibration = self._calibrate_confidence(state, evidence_verification)
        reasoning_consistency = self._validate_reasoning_consistency(state)
        findings = [
            *self._unsupported_claim_findings(evidence_verification, state),
            *self._citation_findings(citation_validation, state),
            *self._retrieval_grounding_findings(retrieval_grounding, state),
            *self._contradiction_findings(contradictions),
            *self._confidence_findings(calibration),
            *self._reasoning_findings(reasoning_consistency, state),
            *self._hallucination_findings(state),
        ]
        score_breakdown = self._score_breakdown(
            evidence_verification,
            citation_validation,
            retrieval_grounding,
            contradictions,
            calibration,
            reasoning_consistency,
            findings,
        )
        reliability_score = self._reliability_score(score_breakdown)
        passed = reliability_score >= self._policy.min_reliability_score and not any(
            finding["severity"] in {"high", "critical"} for finding in findings
        )
        recommendation = self._safety_recommendation(passed, findings, state)
        actions = self._required_actions(recommendation, findings)

        return {
            "passed": passed,
            "reliability_score": reliability_score,
            "confidence": self._critic_confidence(evidence_verification, findings),
            "findings": findings,
            "evidence_verification": evidence_verification,
            "contradictions": contradictions,
            "confidence_calibration": calibration,
            "citation_validation": citation_validation,
            "retrieval_grounding": retrieval_grounding,
            "reasoning_consistency": reasoning_consistency,
            "score_breakdown": score_breakdown,
            "safety_recommendation": recommendation,
            "summary": self._summary(passed, reliability_score, findings),
            "required_actions": actions,
            "policy_version": self._policy.policy_version,
            "model_version": self._policy.model_version,
            "metadata": {
                "validated_agents": "fraud,compliance,retrieval,risk,reporting",
                "finding_count": len(findings),
            },
        }

    def _verify_evidence(self, state: InvestigationState) -> list[EvidenceVerificationResult]:
        citation_count = len(state.get("financial_retrieval", {}).get("citations", []))
        evidence_count = len(state.get("evidence", []))
        retrieval_evidence = len(state.get("financial_retrieval", {}).get("evidence", []))
        fraud_claims = len(state.get("fraud_detection", {}).get("signals", []))
        risk_claims = len(state.get("operational_risk", {}).get("signals", []))
        compliance_claims = len(state.get("compliance_flags", []))
        report = state.get("executive_report", {})
        report_claims = len(report.get("findings", [])) + len(report.get("sections", []))
        report_citations = len(report.get("citations", []))

        return [
            self._verification(
                "fraud_agent",
                fraud_claims,
                min(fraud_claims, evidence_count + retrieval_evidence),
                citation_count,
            ),
            self._verification(
                "retrieval_agent",
                retrieval_evidence,
                retrieval_evidence,
                citation_count,
            ),
            self._verification(
                "risk_scoring_agent",
                risk_claims,
                min(risk_claims, evidence_count + citation_count),
                citation_count,
            ),
            self._verification(
                "compliance_agent",
                compliance_claims,
                min(compliance_claims, evidence_count + citation_count),
                citation_count,
            ),
            self._verification(
                "reporting_agent",
                report_claims,
                min(report_claims, evidence_count + citation_count + report_citations),
                report_citations,
            ),
        ]

    def _verification(
        self,
        target_agent: str,
        checked_claims: int,
        supported_claims: int,
        citation_count: int,
    ) -> EvidenceVerificationResult:
        unsupported = max(0, checked_claims - supported_claims)
        grounding_score = supported_claims / checked_claims if checked_claims else 1.0
        return {
            "target_agent": target_agent,
            "checked_claims": checked_claims,
            "supported_claims": supported_claims,
            "unsupported_claims": unsupported,
            "citation_count": citation_count,
            "grounding_score": round(grounding_score, 2),
        }

    def _validate_citations(self, state: InvestigationState) -> list[CitationValidationResult]:
        retrieval_citations = state.get("financial_retrieval", {}).get("citations", [])
        compliance_citations = state.get("compliance_validation", {}).get("citations", [])
        report = state.get("executive_report", {})
        report_citations = report.get("citations", [])
        report_finding_citation_ids = [
            citation_id
            for finding in report.get("findings", [])
            for citation_id in finding.get("citation_ids", [])
        ]
        retrieval_ids = self._citation_ids(retrieval_citations)
        compliance_ids = self._citation_ids(compliance_citations)
        report_ids = self._citation_ids(report_citations)
        source_ids = retrieval_ids | compliance_ids

        return [
            self._citation_result(
                "retrieval_agent",
                retrieval_citations,
                retrieval_ids,
                retrieval_ids,
                0,
            ),
            self._citation_result(
                "compliance_agent",
                compliance_citations,
                compliance_ids,
                compliance_ids | retrieval_ids,
                0,
            ),
            self._citation_result(
                "reporting_agent",
                report_citations,
                report_ids,
                source_ids,
                len([item for item in report_finding_citation_ids if item not in report_ids]),
            ),
        ]

    def _citation_result(
        self,
        target_agent: str,
        citations: list[dict],
        citation_ids: set[str],
        valid_source_ids: set[str],
        missing_citations: int,
    ) -> CitationValidationResult:
        checked = len(citations)
        invalid = len(
            [citation_id for citation_id in citation_ids if citation_id not in valid_source_ids]
        )
        valid = max(0, checked - invalid)
        support_score = valid / checked if checked else 1.0
        if missing_citations:
            support_score = max(0.0, support_score - min(0.4, missing_citations * 0.1))
        return {
            "target_agent": target_agent,
            "checked_citations": checked,
            "valid_citations": valid,
            "invalid_citations": invalid,
            "missing_citations": missing_citations,
            "citation_support_score": round(support_score, 2),
        }

    def _check_retrieval_grounding(
        self,
        state: InvestigationState,
    ) -> list[RetrievalGroundingResult]:
        retrieval = state.get("financial_retrieval", {})
        retrieval_evidence_count = len(retrieval.get("evidence", []))
        retrieval_citation_count = len(retrieval.get("citations", []))
        report = state.get("executive_report", {})
        report_claims = len(report.get("findings", []))
        report_grounded = len(
            [
                finding
                for finding in report.get("findings", [])
                if finding.get("evidence_ids") or finding.get("citation_ids")
            ]
        )

        return [
            self._grounding_result(
                "retrieval_agent",
                retrieval_evidence_count,
                0,
                retrieval_evidence_count,
                retrieval_citation_count,
            ),
            self._grounding_result(
                "reporting_agent",
                report_grounded,
                max(0, report_claims - report_grounded),
                retrieval_evidence_count,
                retrieval_citation_count,
            ),
        ]

    def _grounding_result(
        self,
        target_agent: str,
        grounded_claims: int,
        ungrounded_claims: int,
        retrieval_evidence_count: int,
        retrieval_citation_count: int,
    ) -> RetrievalGroundingResult:
        total = grounded_claims + ungrounded_claims
        ratio = grounded_claims / total if total else 1.0
        status = "grounded"
        if ratio < self._policy.min_retrieval_grounding_score:
            status = "partial" if grounded_claims else "ungrounded"
        return {
            "target_agent": target_agent,
            "grounded_claims": grounded_claims,
            "ungrounded_claims": ungrounded_claims,
            "retrieval_evidence_count": retrieval_evidence_count,
            "retrieval_citation_count": retrieval_citation_count,
            "grounding_status": status,
        }

    def _detect_contradictions(self, state: InvestigationState) -> list[ContradictionResult]:
        contradictions: list[ContradictionResult] = []
        fraud_band = state.get("fraud_detection", {}).get("risk_band")
        risk_band = state.get("operational_risk", {}).get("risk_band") or state.get("risk_band")
        if fraud_band in {"high", "critical"} and risk_band == "low":
            contradictions.append(
                self._contradiction(
                    "fraud_agent",
                    "risk_scoring_agent",
                    "Fraud agent reports high or critical risk while risk score is low.",
                    "high",
                    self._evidence_ids(state),
                )
            )

        escalation = state.get("operational_risk", {}).get("escalation", {}).get("level")
        if "sanctions_hit" in state.get("compliance_flags", []) and escalation not in {
            "block",
            "regulatory",
        }:
            contradictions.append(
                self._contradiction(
                    "compliance_agent",
                    "risk_scoring_agent",
                    "Sanctions hit is not reflected in escalation recommendation.",
                    "critical",
                    self._evidence_ids(state),
                )
            )
        report_status = state.get("executive_report", {}).get("status")
        if state.get("critic_passed") is False and report_status in {"ready_for_review", "final"}:
            contradictions.append(
                self._contradiction(
                    "critic_agent",
                    "reporting_agent",
                    "Final report path conflicts with a failed critic validation state.",
                    "critical",
                    self._evidence_ids(state),
                )
            )
        return contradictions

    def _contradiction(
        self,
        left_agent: str,
        right_agent: str,
        description: str,
        severity: str,
        evidence_refs: list[str],
    ) -> ContradictionResult:
        return {
            "contradiction_id": f"contradiction_{uuid4().hex}",
            "left_agent": left_agent,
            "right_agent": right_agent,
            "description": description,
            "severity": severity,
            "evidence_refs": evidence_refs,
        }

    def _calibrate_confidence(
        self,
        state: InvestigationState,
        evidence_verification: list[EvidenceVerificationResult],
    ) -> list[ConfidenceCalibrationResult]:
        grounding = {
            item["target_agent"]: item["grounding_score"] for item in evidence_verification
        }
        return [
            self._calibration(
                "fraud_agent",
                float(state.get("fraud_detection", {}).get("confidence", 0.5)),
                grounding.get("fraud_agent", 0.5),
            ),
            self._calibration(
                "retrieval_agent",
                float(state.get("financial_retrieval", {}).get("confidence", 0.5)),
                grounding.get("retrieval_agent", 0.5),
            ),
            self._calibration(
                "risk_scoring_agent",
                float(
                    state.get("operational_risk", {}).get(
                        "confidence",
                        state.get("confidence", 0.5),
                    )
                ),
                grounding.get("risk_scoring_agent", 0.5),
            ),
            self._calibration(
                "compliance_agent",
                float(state.get("compliance_validation", {}).get("confidence", 0.5)),
                grounding.get("compliance_agent", 0.5),
            ),
            self._calibration(
                "reporting_agent",
                float(state.get("executive_report", {}).get("confidence", 0.5)),
                grounding.get("reporting_agent", 0.5),
            ),
        ]

    def _calibration(
        self,
        target_agent: str,
        reported_confidence: float,
        evidence_confidence: float,
    ) -> ConfidenceCalibrationResult:
        calibrated = round((reported_confidence * 0.45) + (evidence_confidence * 0.55), 2)
        delta = round(reported_confidence - calibrated, 2)
        status = "aligned"
        if delta > 0.18:
            status = "overconfident"
        elif delta < -0.18:
            status = "underconfident"
        return {
            "target_agent": target_agent,
            "reported_confidence": round(reported_confidence, 2),
            "evidence_confidence": round(evidence_confidence, 2),
            "calibrated_confidence": calibrated,
            "calibration_delta": delta,
            "status": status,
        }

    def _validate_reasoning_consistency(
        self,
        state: InvestigationState,
    ) -> list[ReasoningConsistencyResult]:
        return [
            self._risk_reasoning_consistency(state),
            self._compliance_reasoning_consistency(state),
            self._report_reasoning_consistency(state),
        ]

    def _risk_reasoning_consistency(
        self,
        state: InvestigationState,
    ) -> ReasoningConsistencyResult:
        notes: list[str] = []
        checked = 2
        passed = 0
        risk_band = state.get("operational_risk", {}).get("risk_band") or state.get("risk_band")
        escalation = state.get("operational_risk", {}).get("escalation", {}).get("level")
        if risk_band in {"high", "critical"} and escalation in {"block", "regulatory", "executive"}:
            passed += 1
        elif risk_band in {"low", "medium"}:
            passed += 1
        else:
            notes.append("Risk band does not align with escalation recommendation.")

        if state.get("fraud_detection", {}).get("signals") or state.get("compliance_flags"):
            passed += 1
        else:
            notes.append("Risk score has limited upstream fraud or compliance rationale.")
        return self._consistency_result("risk_scoring_agent", checked, passed, notes)

    def _compliance_reasoning_consistency(
        self,
        state: InvestigationState,
    ) -> ReasoningConsistencyResult:
        notes: list[str] = []
        checked = 2
        passed = 0
        flags = set(state.get("compliance_flags", []))
        recommendation = state.get("compliance_validation", {}).get("recommendation", {})
        if "sanctions_hit" not in flags or recommendation.get("level") in {"block", "regulatory"}:
            passed += 1
        else:
            notes.append("Sanctions flag does not align with compliance recommendation.")

        citations = state.get("compliance_validation", {}).get("citations", [])
        if not flags or citations:
            passed += 1
        else:
            notes.append("Compliance flags require policy citations.")
        return self._consistency_result("compliance_agent", checked, passed, notes)

    def _report_reasoning_consistency(
        self,
        state: InvestigationState,
    ) -> ReasoningConsistencyResult:
        notes: list[str] = []
        checked = 2
        passed = 0
        report = state.get("executive_report", {})
        report_status = report.get("status")
        if report_status not in {"ready_for_review", "final"} or report.get("findings"):
            passed += 1
        else:
            notes.append("Ready report has no evidence-backed findings.")

        high_risk = state.get("risk_band") in {"high", "critical"} or state.get(
            "operational_risk", {}
        ).get("risk_band") in {"high", "critical"}
        if not high_risk or not report or report.get("citations"):
            passed += 1
        else:
            notes.append("High-risk report requires citations.")
        return self._consistency_result("reporting_agent", checked, passed, notes)

    def _consistency_result(
        self,
        target_agent: str,
        checked_rules: int,
        passed_rules: int,
        notes: list[str],
    ) -> ReasoningConsistencyResult:
        failed = max(0, checked_rules - passed_rules)
        score = passed_rules / checked_rules if checked_rules else 1.0
        return {
            "target_agent": target_agent,
            "checked_rules": checked_rules,
            "passed_rules": passed_rules,
            "failed_rules": failed,
            "consistency_score": round(score, 2),
            "notes": notes,
        }

    def _unsupported_claim_findings(
        self,
        verification: list[EvidenceVerificationResult],
        state: InvestigationState,
    ) -> list[CriticFinding]:
        findings: list[CriticFinding] = []
        for result in verification:
            if result["unsupported_claims"] <= 0:
                continue
            findings.append(
                self._finding(
                    "unsupported_claim",
                    "high" if result["grounding_score"] < 0.5 else "medium",
                    result["target_agent"],
                    f"{result['unsupported_claims']} unsupported claims detected.",
                    "Attach citations or structured evidence before final action.",
                    self._evidence_ids(state),
                    0.84,
                )
            )
        return findings

    def _citation_findings(
        self,
        validation: list[CitationValidationResult],
        state: InvestigationState,
    ) -> list[CriticFinding]:
        findings: list[CriticFinding] = []
        for result in validation:
            if not result["invalid_citations"] and not result["missing_citations"]:
                continue
            severity = "high"
            if result["citation_support_score"] >= self._policy.min_report_citation_support:
                severity = "medium"
            findings.append(
                self._finding(
                    "invalid_citation",
                    severity,
                    result["target_agent"],
                    "Citation validation found missing or invalid citation references.",
                    "Regenerate citations from approved retrieval or policy sources.",
                    self._evidence_ids(state),
                    0.88,
                )
            )
        return findings

    def _retrieval_grounding_findings(
        self,
        grounding: list[RetrievalGroundingResult],
        state: InvestigationState,
    ) -> list[CriticFinding]:
        findings: list[CriticFinding] = []
        for result in grounding:
            if result["grounding_status"] == "grounded":
                continue
            findings.append(
                self._finding(
                    "retrieval_grounding_gap",
                    "high" if result["grounding_status"] == "ungrounded" else "medium",
                    result["target_agent"],
                    "Output contains claims that are not grounded in retrieval evidence.",
                    "Run evidence expansion and bind claims to retrieved source citations.",
                    self._evidence_ids(state),
                    0.86,
                )
            )
        return findings

    def _contradiction_findings(
        self,
        contradictions: list[ContradictionResult],
    ) -> list[CriticFinding]:
        return [
            self._finding(
                "contradiction",
                contradiction["severity"],
                f"{contradiction['left_agent']}:{contradiction['right_agent']}",
                contradiction["description"],
                "Resolve agent disagreement before escalation.",
                contradiction["evidence_refs"],
                0.9,
            )
            for contradiction in contradictions
        ]

    def _confidence_findings(
        self,
        calibration: list[ConfidenceCalibrationResult],
    ) -> list[CriticFinding]:
        findings: list[CriticFinding] = []
        for result in calibration:
            if result["status"] != "overconfident":
                continue
            findings.append(
                self._finding(
                    "confidence_miscalibration",
                    "medium",
                    result["target_agent"],
                    "Reported confidence exceeds evidence-calibrated confidence.",
                    "Lower confidence or add stronger evidence support.",
                    [],
                    0.78,
                )
            )
        return findings

    def _reasoning_findings(
        self,
        consistency: list[ReasoningConsistencyResult],
        state: InvestigationState,
    ) -> list[CriticFinding]:
        findings: list[CriticFinding] = []
        for result in consistency:
            if result["failed_rules"] <= 0:
                continue
            findings.append(
                self._finding(
                    "reasoning_inconsistency",
                    "high" if result["consistency_score"] < 0.5 else "medium",
                    result["target_agent"],
                    "; ".join(result["notes"]) or "Reasoning consistency rule failed.",
                    "Revise the agent output so conclusions follow from validated evidence.",
                    self._evidence_ids(state),
                    0.82,
                )
            )
        return findings

    def _hallucination_findings(self, state: InvestigationState) -> list[CriticFinding]:
        findings: list[CriticFinding] = []
        retrieval = state.get("financial_retrieval")
        high_risk = state.get("risk_band") in {"high", "critical"} or state.get(
            "operational_risk", {}
        ).get("risk_band") in {"high", "critical"}
        if high_risk and not retrieval:
            findings.append(
                self._finding(
                    "missing_citation",
                    "high",
                    "workflow",
                    "High-risk workflow has no retrieval citations attached.",
                    "Run financial retrieval before final report or escalation.",
                    self._evidence_ids(state),
                    0.86,
                )
            )
        return findings

    def _finding(
        self,
        finding_type: str,
        severity: str,
        target_agent: str,
        claim: str,
        recommendation: str,
        evidence_refs: list[str],
        confidence: float,
    ) -> CriticFinding:
        return {
            "finding_id": f"critic_{uuid4().hex}",
            "finding_type": finding_type,
            "severity": severity,
            "target_agent": target_agent,
            "claim": claim,
            "explanation": recommendation,
            "evidence_refs": evidence_refs,
            "recommendation": recommendation,
            "confidence": confidence,
        }

    def _score_breakdown(
        self,
        verification: list[EvidenceVerificationResult],
        citation_validation: list[CitationValidationResult],
        retrieval_grounding: list[RetrievalGroundingResult],
        contradictions: list[ContradictionResult],
        calibration: list[ConfidenceCalibrationResult],
        consistency: list[ReasoningConsistencyResult],
        findings: list[CriticFinding],
    ) -> ReliabilityScoreBreakdown:
        grounding = self._average([item["grounding_score"] for item in verification])
        citation_support = self._average(
            [item["citation_support_score"] for item in citation_validation]
        )
        grounded_status = {
            "grounded": 1.0,
            "partial": 0.6,
            "ungrounded": 0.0,
        }
        retrieval_score = self._average(
            [grounded_status[item["grounding_status"]] for item in retrieval_grounding]
        )
        contradiction_score = max(0.0, 1.0 - min(0.5, len(contradictions) * 0.2))
        calibration_score = max(
            0.0,
            1.0
            - min(
                0.5,
                sum(abs(item["calibration_delta"]) for item in calibration) / 5,
            ),
        )
        consistency_score = self._average(
            [item["consistency_score"] for item in consistency]
        )
        finding_penalty = min(0.35, len(findings) * 0.04)
        return {
            "grounding_score": round((grounding + retrieval_score) / 2, 2),
            "citation_support_score": round(citation_support, 2),
            "contradiction_score": round(contradiction_score, 2),
            "confidence_calibration_score": round(calibration_score, 2),
            "reasoning_consistency_score": round(consistency_score, 2),
            "finding_penalty": round(finding_penalty, 2),
        }

    def _reliability_score(self, breakdown: ReliabilityScoreBreakdown) -> float:
        score = (
            0.25 * breakdown["grounding_score"]
            + 0.2 * breakdown["citation_support_score"]
            + 0.2 * breakdown["contradiction_score"]
            + 0.15 * breakdown["confidence_calibration_score"]
            + 0.1 * breakdown["reasoning_consistency_score"]
            + 0.1
        )
        score -= breakdown["finding_penalty"]
        return round(max(0.0, min(1.0, score)), 2)

    def _legacy_reliability_score(
        self,
        verification: list[EvidenceVerificationResult],
        contradictions: list[ContradictionResult],
        calibration: list[ConfidenceCalibrationResult],
        findings: list[CriticFinding],
    ) -> float:
        grounding = self._average([item["grounding_score"] for item in verification])
        contradiction_penalty = min(0.35, len(contradictions) * 0.16)
        calibration_penalty = min(
            0.2,
            sum(abs(item["calibration_delta"]) for item in calibration) / 5,
        )
        finding_penalty = min(0.25, len(findings) * 0.04)
        score = grounding - contradiction_penalty - calibration_penalty - finding_penalty
        return round(max(0.0, score), 2)

    def _average(self, values: list[float]) -> float:
        return sum(values) / len(values) if values else 1.0

    def _critic_confidence(
        self,
        verification: list[EvidenceVerificationResult],
        findings: list[CriticFinding],
    ) -> float:
        checked_claims = sum(item["checked_claims"] for item in verification)
        base = min(0.9, 0.55 + checked_claims * 0.025)
        if findings:
            base = min(0.96, base + 0.05)
        return round(base, 2)

    def _safety_recommendation(
        self,
        passed: bool,
        findings: list[CriticFinding],
        state: InvestigationState,
    ) -> str:
        if any(finding["severity"] == "critical" for finding in findings):
            return "block_final_action"
        if any(finding["severity"] == "high" for finding in findings):
            return "human_review"
        if any(
            finding["finding_type"]
            in {
                "unsupported_claim",
                "missing_citation",
                "invalid_citation",
                "retrieval_grounding_gap",
            }
            for finding in findings
        ):
            return "expand_evidence"
        if not passed or state.get("critic_passed") is False:
            return "revise_outputs"
        return "continue"

    def _required_actions(self, recommendation: str, findings: list[CriticFinding]) -> list[str]:
        actions: list[str] = []
        if recommendation in {"expand_evidence", "human_review", "block_final_action"}:
            actions.append("expand_evidence")
        if recommendation in {"human_review", "block_final_action"}:
            actions.append("senior_review")
        if any(finding["finding_type"] == "confidence_miscalibration" for finding in findings):
            actions.append("recalibrate_confidence")
        if any(finding["finding_type"] == "contradiction" for finding in findings):
            actions.append("resolve_agent_contradictions")
        if any(
            finding["finding_type"] in {"invalid_citation", "missing_citation"}
            for finding in findings
        ):
            actions.append("repair_citations")
        if any(finding["finding_type"] == "retrieval_grounding_gap" for finding in findings):
            actions.append("rerun_retrieval_grounding")
        return actions or ["continue_workflow"]

    def _summary(
        self,
        passed: bool,
        reliability_score: float,
        findings: list[CriticFinding],
    ) -> str:
        status = "passed" if passed else "failed"
        return (
            f"Critic validation {status} with reliability score {reliability_score} "
            f"and {len(findings)} findings."
        )

    def _evidence_ids(self, state: InvestigationState) -> list[str]:
        return [item["evidence_id"] for item in state.get("evidence", [])]

    def _citation_ids(self, citations: list[dict]) -> set[str]:
        return {
            str(citation["citation_id"])
            for citation in citations
            if citation.get("citation_id")
        }
