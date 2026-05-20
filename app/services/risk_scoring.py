from dataclasses import dataclass

from app.core.graph.state import InvestigationState
from app.core.graph.state_schemas import (
    EscalationLevel,
    EscalationRecommendation,
    OperationalRiskScore,
    RiskBand,
    RiskSignalScore,
)


@dataclass(frozen=True)
class RiskScoringPolicy:
    fraud_weight: float = 0.32
    compliance_weight: float = 0.24
    anomaly_weight: float = 0.16
    retrieval_weight: float = 0.1
    critic_weight: float = 0.1
    operational_context_weight: float = 0.08
    policy_version: str = "operational-risk-policy-v1"
    scoring_model_version: str = "weighted-operational-risk-v1"


class RiskScoringService:
    """Explainable weighted risk scoring service for operational investigations."""

    def __init__(self, policy: RiskScoringPolicy | None = None) -> None:
        self._policy = policy or RiskScoringPolicy()

    async def score(self, state: InvestigationState) -> OperationalRiskScore:
        signals = [
            self._fraud_signal(state),
            self._compliance_signal(state),
            self._anomaly_signal(state),
            self._retrieval_signal(state),
            self._critic_signal(state),
            self._operational_context_signal(state),
        ]
        aggregate = round(sum(signal["weighted_score"] for signal in signals), 2)
        severity_score = self._severity_score(aggregate, state)
        risk_band = self._risk_band(severity_score)
        confidence = self._confidence(signals, state)
        critic_adjustments = self._critic_adjustments(state)
        evidence_gaps = self._evidence_gaps(state)
        escalation = self._escalation(severity_score, risk_band, state, evidence_gaps)
        actions = self._actions(escalation, evidence_gaps, state)

        return {
            "aggregate_score": aggregate,
            "severity_score": severity_score,
            "risk_band": risk_band,
            "confidence": confidence,
            "signals": signals,
            "escalation": escalation,
            "critic_adjustments": critic_adjustments,
            "evidence_gaps": evidence_gaps,
            "recommended_actions": actions,
            "explanation": self._explanation(severity_score, risk_band, signals, escalation),
            "policy_version": self._policy.policy_version,
            "scoring_model_version": self._policy.scoring_model_version,
        }

    def _fraud_signal(self, state: InvestigationState) -> RiskSignalScore:
        fraud_detection = state.get("fraud_detection")
        raw = float(
            fraud_detection["fraud_score"] if fraud_detection else state.get("fraud_score", 0.0)
        )
        confidence = float(
            fraud_detection["confidence"] if fraud_detection else state.get("confidence", 0.5)
        )
        return self._signal(
            "fraud",
            raw,
            self._policy.fraud_weight,
            confidence,
            "Fraud risk from fraud signals and detection score.",
        )

    def _compliance_signal(self, state: InvestigationState) -> RiskSignalScore:
        flags = state.get("compliance_flags", [])
        base = float(state.get("compliance_score", 0.0))
        if "sanctions_hit" in flags:
            base = max(base, 95.0)
        elif "sar_threshold_met" in flags:
            base = max(base, 75.0)
        elif flags:
            base = max(base, 55.0)
        return self._signal(
            "compliance",
            base,
            self._policy.compliance_weight,
            0.86 if flags else 0.62,
            "Compliance score from policy flags and violation severity.",
        )

    def _anomaly_signal(self, state: InvestigationState) -> RiskSignalScore:
        transaction_analysis = state.get("transaction_analysis")
        raw = float(transaction_analysis["anomaly_score"] if transaction_analysis else 0.0)
        confidence = float(transaction_analysis["confidence"] if transaction_analysis else 0.45)
        return self._signal(
            "anomaly",
            raw,
            self._policy.anomaly_weight,
            confidence,
            "Transaction anomaly score from behavior, velocity, and chain analysis.",
        )

    def _retrieval_signal(self, state: InvestigationState) -> RiskSignalScore:
        retrieval = state.get("financial_retrieval")
        if retrieval is None:
            raw = 25.0
            confidence = 0.35
            rationale = "No grounded retrieval evidence is attached."
        else:
            raw = min(100.0, len(retrieval["evidence"]) * 15.0 + retrieval["confidence"] * 40.0)
            confidence = retrieval["confidence"]
            rationale = "Grounded retrieval evidence and citations support decisioning."
        return self._signal(
            "retrieval_evidence",
            raw,
            self._policy.retrieval_weight,
            confidence,
            rationale,
        )

    def _critic_signal(self, state: InvestigationState) -> RiskSignalScore:
        critic_notes = state.get("critic_notes", [])
        if state.get("critic_passed") is False:
            raw = 70.0
            confidence = 0.75
            rationale = "Critic feedback found unresolved quality or evidence concerns."
        elif critic_notes:
            raw = 45.0
            confidence = 0.65
            rationale = "Critic feedback contains review notes."
        else:
            raw = 15.0
            confidence = 0.55
            rationale = "No adverse critic feedback is present."
        return self._signal(
            "critic_feedback",
            raw,
            self._policy.critic_weight,
            confidence,
            rationale,
        )

    def _operational_context_signal(self, state: InvestigationState) -> RiskSignalScore:
        evidence_count = len(state.get("evidence", []))
        retry_count = sum(state.get("retry_counts", {}).values())
        raw = min(100.0, evidence_count * 5.0 + retry_count * 8.0)
        return self._signal(
            "operational_context",
            raw,
            self._policy.operational_context_weight,
            0.68,
            "Operational context from evidence volume and workflow retry pressure.",
        )

    def _signal(
        self,
        name: str,
        raw_score: float,
        weight: float,
        confidence: float,
        rationale: str,
    ) -> RiskSignalScore:
        raw = max(0.0, min(raw_score, 100.0))
        return {
            "signal_name": name,
            "raw_score": round(raw, 2),
            "weight": weight,
            "weighted_score": round(raw * weight, 2),
            "confidence": round(max(0.0, min(confidence, 1.0)), 2),
            "rationale": rationale,
        }

    def _severity_score(self, aggregate: float, state: InvestigationState) -> float:
        flags = state.get("compliance_flags", [])
        severity = aggregate
        if "sanctions_hit" in flags:
            severity = max(severity, 95.0)
        if state.get("fraud_detection", {}).get("escalation_recommendation") == "temporary_hold":
            severity = max(severity, 90.0)
        if state.get("critic_passed") is False:
            severity = min(100.0, severity + 8.0)
        return round(min(severity, 100.0), 2)

    def _risk_band(self, score: float) -> RiskBand:
        if score >= 90:
            return "critical"
        if score >= 70:
            return "high"
        if score >= 40:
            return "medium"
        return "low"

    def _confidence(self, signals: list[RiskSignalScore], state: InvestigationState) -> float:
        weighted_confidence = sum(signal["confidence"] * signal["weight"] for signal in signals)
        evidence_bonus = min(0.12, len(state.get("evidence", [])) * 0.015)
        retrieval_bonus = 0.08 if state.get("financial_retrieval", {}).get("citations") else 0.0
        return round(min(0.97, weighted_confidence + evidence_bonus + retrieval_bonus), 2)

    def _critic_adjustments(self, state: InvestigationState) -> list[str]:
        adjustments: list[str] = []
        if state.get("critic_passed") is False:
            adjustments.append("critic_failed_score_increase")
        for note in state.get("critic_notes", []):
            adjustments.append(f"critic_note:{note}")
        return adjustments

    def _evidence_gaps(self, state: InvestigationState) -> list[str]:
        gaps: list[str] = []
        if not state.get("financial_retrieval", {}).get("citations"):
            gaps.append("missing_retrieval_citations")
        if not state.get("evidence"):
            gaps.append("missing_structured_evidence")
        if not state.get("fraud_detection"):
            gaps.append("missing_fraud_detection_result")
        return gaps

    def _escalation(
        self,
        severity_score: float,
        risk_band: RiskBand,
        state: InvestigationState,
        evidence_gaps: list[str],
    ) -> EscalationRecommendation:
        flags = state.get("compliance_flags", [])
        if "sanctions_hit" in flags or risk_band == "critical":
            return self._recommendation(
                "block",
                1,
                "compliance_officer",
                "Critical risk or sanctions signal requires immediate controlled escalation.",
                ["place_temporary_hold", "senior_review", "prepare_regulatory_packet"],
            )
        if "sar_threshold_met" in flags:
            return self._recommendation(
                "regulatory",
                2,
                "compliance_officer",
                "SAR threshold signal requires regulatory review.",
                ["analyst_review", "prepare_sar_draft"],
            )
        if risk_band == "high":
            return self._recommendation(
                "senior_review",
                3,
                "senior_investigator",
                "High operational risk requires senior investigator approval.",
                ["senior_review", "expand_evidence" if evidence_gaps else "finalize_report"],
            )
        if risk_band == "medium":
            return self._recommendation(
                "analyst_review",
                4,
                "risk_analyst",
                "Medium operational risk requires analyst validation.",
                ["analyst_review"],
            )
        return self._recommendation(
            "none",
            5,
            "system",
            f"Risk score {severity_score} does not require escalation.",
            ["close_as_low_risk"],
        )

    def _recommendation(
        self,
        level: EscalationLevel,
        priority: int,
        required_role: str,
        rationale: str,
        actions: list[str],
    ) -> EscalationRecommendation:
        return {
            "level": level,
            "priority": priority,
            "required_role": required_role,
            "rationale": rationale,
            "recommended_actions": actions,
        }

    def _actions(
        self,
        escalation: EscalationRecommendation,
        evidence_gaps: list[str],
        state: InvestigationState,
    ) -> list[str]:
        actions = list(escalation["recommended_actions"])
        if evidence_gaps and escalation["level"] != "none":
            actions.append("resolve_evidence_gaps")
        if state.get("financial_retrieval", {}).get("citations"):
            actions.append("attach_retrieval_citations")
        return list(dict.fromkeys(actions))

    def _explanation(
        self,
        severity_score: float,
        risk_band: RiskBand,
        signals: list[RiskSignalScore],
        escalation: EscalationRecommendation,
    ) -> str:
        top = sorted(signals, key=lambda signal: signal["weighted_score"], reverse=True)[:3]
        drivers = ", ".join(signal["signal_name"] for signal in top)
        return (
            f"Operational risk score {severity_score} is {risk_band}. "
            f"Primary drivers: {drivers}. Escalation: {escalation['level']}."
        )
