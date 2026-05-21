from dataclasses import dataclass
from uuid import uuid4

from app.core.graph.state import InvestigationState
from app.core.graph.state_schemas import (
    ConfidenceCalibrationResult,
    ContradictionResult,
    CriticFinding,
    CriticValidationResult,
    EvidenceVerificationResult,
)


@dataclass(frozen=True)
class CriticPolicy:
    min_reliability_score: float = 0.72
    high_confidence_threshold: float = 0.85
    min_citation_count_for_high_risk: int = 1
    policy_version: str = "enterprise-critic-policy-v1"
    model_version: str = "deterministic-critic-v1"


class CriticService:
    """Enterprise reliability critic for grounded AI workflow outputs."""

    def __init__(self, policy: CriticPolicy | None = None) -> None:
        self._policy = policy or CriticPolicy()

    async def validate(self, state: InvestigationState) -> CriticValidationResult:
        evidence_verification = self._verify_evidence(state)
        contradictions = self._detect_contradictions(state)
        calibration = self._calibrate_confidence(state, evidence_verification)
        findings = [
            *self._unsupported_claim_findings(evidence_verification, state),
            *self._contradiction_findings(contradictions),
            *self._confidence_findings(calibration),
            *self._hallucination_findings(state),
        ]
        reliability_score = self._reliability_score(
            evidence_verification,
            contradictions,
            calibration,
            findings,
        )
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
            "safety_recommendation": recommendation,
            "summary": self._summary(passed, reliability_score, findings),
            "required_actions": actions,
            "policy_version": self._policy.policy_version,
            "model_version": self._policy.model_version,
            "metadata": {
                "validated_agents": "fraud,retrieval,risk,compliance",
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

    def _reliability_score(
        self,
        verification: list[EvidenceVerificationResult],
        contradictions: list[ContradictionResult],
        calibration: list[ConfidenceCalibrationResult],
        findings: list[CriticFinding],
    ) -> float:
        grounding = sum(item["grounding_score"] for item in verification) / len(verification)
        contradiction_penalty = min(0.35, len(contradictions) * 0.16)
        calibration_penalty = min(
            0.2,
            sum(abs(item["calibration_delta"]) for item in calibration) / 5,
        )
        finding_penalty = min(0.25, len(findings) * 0.04)
        score = grounding - contradiction_penalty - calibration_penalty - finding_penalty
        return round(max(0.0, score), 2)

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
            finding["finding_type"] in {"unsupported_claim", "missing_citation"}
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
