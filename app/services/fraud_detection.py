from dataclasses import dataclass
from uuid import uuid4

from app.core.graph.state_schemas import (
    FraudDetectionResult,
    FraudEvidence,
    FraudHeuristicResult,
    FraudSignalType,
    TransactionAnalysisResult,
    TransactionObservation,
)
from app.services.transaction_analysis import TransactionAnalysisService


@dataclass(frozen=True)
class FraudDetectionPolicy:
    high_amount_threshold: float = 10_000.0
    critical_amount_threshold: float = 50_000.0
    velocity_score_threshold: float = 40.0
    geo_inconsistency_threshold: int = 2
    risky_merchant_categories: tuple[str, ...] = (
        "crypto",
        "gambling",
        "money_services",
        "high_risk_marketplace",
    )
    device_mismatch_weight: float = 16.0
    structuring_weight: float = 28.0
    rapid_chain_weight: float = 18.0


class FraudNarrativeProvider:
    """AI-assisted extension point for fraud explanations.

    Production deployments can replace this deterministic provider with a governed model call that
    receives only structured facts and returns a bounded narrative.
    """

    async def summarize(self, result: FraudDetectionResult) -> str:
        signals = ", ".join(result["signals"]) or "no material fraud signals"
        return (
            f"Fraud review identified {signals} with {result['risk_band']} risk "
            f"and confidence {result['confidence']}."
        )


class FraudDetectionService:
    """Rule-based and AI-assisted fraud detection service with explainable outputs."""

    def __init__(
        self,
        *,
        policy: FraudDetectionPolicy | None = None,
        transaction_analysis_service: TransactionAnalysisService | None = None,
        narrative_provider: FraudNarrativeProvider | None = None,
    ) -> None:
        self._policy = policy or FraudDetectionPolicy()
        self._transaction_analysis = transaction_analysis_service or TransactionAnalysisService()
        self._narrative_provider = narrative_provider or FraudNarrativeProvider()

    async def detect(
        self,
        *,
        transaction_id: str,
        transactions: list[TransactionObservation],
        transaction_analysis: TransactionAnalysisResult | None = None,
        customer_jurisdiction: str | None = None,
        device_id: str | None = None,
        known_device_ids: list[str] | None = None,
        merchant_category: str | None = None,
    ) -> FraudDetectionResult:
        analysis = transaction_analysis or await self._transaction_analysis.analyze(
            transaction_id=transaction_id,
            transactions=transactions,
        )
        evidence: list[FraudEvidence] = []
        heuristics = [
            self._amount_anomaly(analysis, evidence),
            self._velocity_anomaly(analysis, evidence),
            self._geo_inconsistency(
                analysis,
                evidence,
                customer_jurisdiction=customer_jurisdiction,
            ),
            self._device_mismatch(
                analysis,
                evidence,
                device_id=device_id,
                known_device_ids=known_device_ids or [],
            ),
            self._merchant_risk(
                analysis,
                evidence,
                merchant_category=merchant_category,
            ),
            self._behavioral_deviation(analysis, evidence),
            self._structuring_signal(analysis, evidence),
            self._rapid_chain_movement(analysis, evidence),
        ]
        triggered = [item for item in heuristics if item["triggered"]]
        fraud_score = self._score(triggered, analysis)
        risk_band = self._risk_band(fraud_score)
        confidence = self._confidence(triggered, evidence, analysis)
        signals = [item["signal_type"] for item in triggered]
        geographic_inconsistencies = [
            item["rationale"] for item in triggered if item["signal_type"] == "geo_inconsistency"
        ]
        suspicious_behaviors = [item["rationale"] for item in triggered]

        result: FraudDetectionResult = {
            "transaction_id": transaction_id,
            "fraud_score": fraud_score,
            "risk_band": risk_band,
            "confidence": confidence,
            "signals": signals,
            "evidence": evidence,
            "heuristics": heuristics,
            "geographic_inconsistencies": geographic_inconsistencies,
            "suspicious_behaviors": suspicious_behaviors,
            "escalation_recommendation": self._escalation(fraud_score, signals),
            "explanation": self._explanation(triggered, fraud_score, risk_band),
            "recommended_actions": self._actions(fraud_score, signals),
        }
        result["ai_assisted_summary"] = await self._narrative_provider.summarize(result)
        return result

    def _amount_anomaly(
        self,
        analysis: TransactionAnalysisResult,
        evidence: list[FraudEvidence],
    ) -> FraudHeuristicResult:
        max_amount = analysis["aggregate"]["max_amount"]
        triggered = max_amount >= self._policy.high_amount_threshold
        severity_weight = 30.0 if max_amount >= self._policy.critical_amount_threshold else 18.0
        return self._heuristic(
            "amount_anomaly",
            "amount_anomaly",
            triggered,
            severity_weight if triggered else 0.0,
            f"Maximum transaction amount is {max_amount}.",
            analysis,
            evidence,
            0.78,
        )

    def _velocity_anomaly(
        self,
        analysis: TransactionAnalysisResult,
        evidence: list[FraudEvidence],
    ) -> FraudHeuristicResult:
        rate = analysis["temporal"]["transactions_per_hour"]
        triggered = analysis["anomaly_score"] >= self._policy.velocity_score_threshold and rate >= 5
        return self._heuristic(
            "velocity_anomaly",
            "velocity_anomaly",
            triggered,
            20.0 if triggered else 0.0,
            f"Observed transaction velocity is {rate} transactions per hour.",
            analysis,
            evidence,
            0.82,
        )

    def _geo_inconsistency(
        self,
        analysis: TransactionAnalysisResult,
        evidence: list[FraudEvidence],
        *,
        customer_jurisdiction: str | None,
    ) -> FraudHeuristicResult:
        cross_border = any(item["indicator"] == "cross_border" for item in analysis["indicators"])
        triggered = cross_border and customer_jurisdiction is not None
        rationale = "Transaction activity spans jurisdictions inconsistent with customer profile."
        return self._heuristic(
            "geo_inconsistency",
            "geo_inconsistency",
            triggered,
            17.0 if triggered else 0.0,
            rationale,
            analysis,
            evidence,
            0.74,
        )

    def _device_mismatch(
        self,
        analysis: TransactionAnalysisResult,
        evidence: list[FraudEvidence],
        *,
        device_id: str | None,
        known_device_ids: list[str],
    ) -> FraudHeuristicResult:
        triggered = bool(device_id and known_device_ids and device_id not in known_device_ids)
        return self._heuristic(
            "device_mismatch",
            "device_mismatch",
            triggered,
            self._policy.device_mismatch_weight if triggered else 0.0,
            "Current device is not present in known customer device history.",
            analysis,
            evidence,
            0.7,
        )

    def _merchant_risk(
        self,
        analysis: TransactionAnalysisResult,
        evidence: list[FraudEvidence],
        *,
        merchant_category: str | None,
    ) -> FraudHeuristicResult:
        triggered = bool(
            merchant_category and merchant_category in self._policy.risky_merchant_categories
        )
        return self._heuristic(
            "merchant_risk",
            "merchant_risk",
            triggered,
            12.0 if triggered else 0.0,
            f"Merchant category {merchant_category or 'unknown'} evaluated for risk.",
            analysis,
            evidence,
            0.66,
        )

    def _behavioral_deviation(
        self,
        analysis: TransactionAnalysisResult,
        evidence: list[FraudEvidence],
    ) -> FraudHeuristicResult:
        triggered = (
            analysis["aggregate"]["transaction_count"] >= 4
            or analysis["anomaly_score"] >= 70
        )
        return self._heuristic(
            "behavioral_deviation",
            "behavioral_deviation",
            triggered,
            16.0 if triggered else 0.0,
            "Transaction behavior deviates from baseline review thresholds.",
            analysis,
            evidence,
            0.76,
        )

    def _structuring_signal(
        self,
        analysis: TransactionAnalysisResult,
        evidence: list[FraudEvidence],
    ) -> FraudHeuristicResult:
        triggered = any(item["indicator"] == "structuring" for item in analysis["indicators"])
        return self._heuristic(
            "structuring_signal",
            "structuring_signal",
            triggered,
            self._policy.structuring_weight if triggered else 0.0,
            "Near-threshold activity suggests possible structuring.",
            analysis,
            evidence,
            0.88,
        )

    def _rapid_chain_movement(
        self,
        analysis: TransactionAnalysisResult,
        evidence: list[FraudEvidence],
    ) -> FraudHeuristicResult:
        indicator_names = {item["indicator"] for item in analysis["indicators"]}
        triggered = bool({"rapid_movement", "chain_depth"} & indicator_names)
        return self._heuristic(
            "rapid_chain_movement",
            "rapid_chain_movement",
            triggered,
            self._policy.rapid_chain_weight if triggered else 0.0,
            "Rapid movement or chain depth indicates possible layering behavior.",
            analysis,
            evidence,
            0.8,
        )

    def _heuristic(
        self,
        heuristic_id: str,
        signal_type: FraudSignalType,
        triggered: bool,
        score_delta: float,
        rationale: str,
        analysis: TransactionAnalysisResult,
        evidence: list[FraudEvidence],
        confidence: float,
    ) -> FraudHeuristicResult:
        evidence_ids: list[str] = []
        if triggered:
            fraud_evidence = self._evidence(
                signal_type,
                rationale,
                analysis,
                score_delta,
                confidence,
            )
            evidence.append(fraud_evidence)
            evidence_ids.append(fraud_evidence["evidence_id"])
        return {
            "heuristic_id": heuristic_id,
            "signal_type": signal_type,
            "triggered": triggered,
            "score_delta": round(score_delta, 2),
            "rationale": rationale,
            "evidence_ids": evidence_ids,
            "confidence": confidence,
        }

    def _evidence(
        self,
        signal_type: FraudSignalType,
        description: str,
        analysis: TransactionAnalysisResult,
        weight: float,
        confidence: float,
    ) -> FraudEvidence:
        transaction_ids = sorted(
            {
                tx_id
                for indicator in analysis["indicators"]
                for tx_id in indicator["evidence_transaction_ids"]
            }
        ) or [analysis["transaction_id"]]
        return {
            "evidence_id": f"fraud_ev_{uuid4().hex}",
            "signal_type": signal_type,
            "description": description,
            "source": "fraud_detection_ruleset_v1",
            "transaction_ids": transaction_ids,
            "weight": round(weight, 2),
            "confidence": confidence,
        }

    def _score(
        self,
        heuristics: list[FraudHeuristicResult],
        analysis: TransactionAnalysisResult,
    ) -> float:
        score = analysis["anomaly_score"] * 0.35
        score += sum(item["score_delta"] * item["confidence"] for item in heuristics)
        return round(min(score, 100.0), 2)

    def _risk_band(self, score: float) -> str:
        if score >= 90:
            return "critical"
        if score >= 70:
            return "high"
        if score >= 40:
            return "medium"
        return "low"

    def _confidence(
        self,
        heuristics: list[FraudHeuristicResult],
        evidence: list[FraudEvidence],
        analysis: TransactionAnalysisResult,
    ) -> float:
        signal_factor = min(0.22, len(heuristics) * 0.035)
        evidence_factor = min(0.18, len(evidence) * 0.03)
        confidence = 0.5 + signal_factor + evidence_factor + analysis["confidence"] * 0.15
        return round(min(confidence, 0.97), 2)

    def _escalation(
        self,
        fraud_score: float,
        signals: list[FraudSignalType],
    ) -> str:
        if fraud_score >= 90:
            return "temporary_hold"
        if "structuring_signal" in signals or fraud_score >= 75:
            return "senior_review"
        if fraud_score >= 50:
            return "analyst_review"
        return "none"

    def _actions(self, fraud_score: float, signals: list[FraudSignalType]) -> list[str]:
        actions: list[str] = []
        if fraud_score >= 90:
            actions.extend(["place_temporary_hold", "senior_review"])
        elif fraud_score >= 70:
            actions.append("senior_review")
        elif fraud_score >= 40:
            actions.append("analyst_review")
        else:
            actions.append("continue_standard_workflow")
        if "geo_inconsistency" in signals:
            actions.append("verify_customer_location")
        if "rapid_chain_movement" in signals:
            actions.append("trace_transaction_chain")
        if "structuring_signal" in signals:
            actions.append("prepare_sar_review")
        return actions

    def _explanation(
        self,
        heuristics: list[FraudHeuristicResult],
        fraud_score: float,
        risk_band: str,
    ) -> str:
        if not heuristics:
            return f"Fraud score {fraud_score} is {risk_band}; no major heuristics triggered."
        rationales = " ".join(item["rationale"] for item in heuristics[:4])
        return f"Fraud score {fraud_score} is {risk_band}. {rationales}"
