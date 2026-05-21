from dataclasses import dataclass
from uuid import uuid4

from app.core.graph.state import InvestigationState
from app.core.graph.state_schemas import (
    ComplianceCitation,
    ComplianceRecommendation,
    ComplianceRuleResult,
    ComplianceValidationResult,
)


@dataclass(frozen=True)
class CompliancePolicy:
    reporting_threshold: float = 10_000.0
    high_value_threshold: float = 50_000.0
    sanctioned_jurisdictions: tuple[str, ...] = ("IR", "KP", "SY")
    allowed_kyc_statuses: tuple[str, ...] = ("verified", "enhanced_due_diligence")
    policy_version: str = "enterprise-compliance-policy-v1"


class ComplianceRuleEngine:
    """Deterministic rule engine for AML-inspired enterprise compliance validation."""

    def __init__(self, policy: CompliancePolicy | None = None) -> None:
        self._policy = policy or CompliancePolicy()

    def evaluate(self, state: InvestigationState) -> list[ComplianceRuleResult]:
        citations = self._policy_refs(state)
        return [
            self._kyc_rule(state, citations),
            self._sanctions_rule(state, citations),
            self._threshold_rule(state, citations),
            self._aml_behavior_rule(state, citations),
            self._policy_grounding_rule(state, citations),
        ]

    def _kyc_rule(
        self,
        state: InvestigationState,
        citations: list[str],
    ) -> ComplianceRuleResult:
        kyc_status = state.get("subject", {}).get(
            "kyc_status",
            state.get("customer_profile", {}).get("kyc_status", "unknown"),
        )
        passed = kyc_status in self._policy.allowed_kyc_statuses
        return self._result(
            "kyc_status_valid",
            "kyc",
            passed,
            "medium" if not passed else "low",
            f"KYC status is {kyc_status}.",
            citations,
            self._evidence_ids(state),
            0.84,
        )

    def _sanctions_rule(
        self,
        state: InvestigationState,
        citations: list[str],
    ) -> ComplianceRuleResult:
        jurisdiction = str(state.get("jurisdiction", "US")).upper()
        passed = jurisdiction not in self._policy.sanctioned_jurisdictions
        return self._result(
            "sanctions_jurisdiction_screen",
            "sanctions",
            passed,
            "critical" if not passed else "low",
            f"Transaction jurisdiction {jurisdiction} screened against sanctions policy.",
            citations,
            self._evidence_ids(state),
            0.9,
        )

    def _threshold_rule(
        self,
        state: InvestigationState,
        citations: list[str],
    ) -> ComplianceRuleResult:
        amount = float(state.get("transaction_amount", 0.0))
        passed = amount < self._policy.reporting_threshold
        severity = "high" if amount >= self._policy.high_value_threshold else "medium"
        return self._result(
            "reporting_threshold_check",
            "threshold",
            passed,
            severity if not passed else "low",
            f"Transaction amount {amount} evaluated against reporting threshold.",
            citations,
            self._evidence_ids(state),
            0.86,
        )

    def _aml_behavior_rule(
        self,
        state: InvestigationState,
        citations: list[str],
    ) -> ComplianceRuleResult:
        fraud_signals = set(state.get("fraud_detection", {}).get("signals", []))
        anomaly_indicators = {
            item["indicator"]
            for item in state.get("transaction_analysis", {}).get("indicators", [])
        }
        suspicious = bool(
            {"structuring_signal", "rapid_chain_movement"} & fraud_signals
            or {"structuring", "rapid_movement", "cross_border"} & anomaly_indicators
        )
        return self._result(
            "aml_suspicious_activity_review",
            "suspicious_activity",
            not suspicious,
            "high" if suspicious else "low",
            "AML review evaluated structuring, rapid movement, and cross-border indicators.",
            citations,
            self._evidence_ids(state),
            0.82,
        )

    def _policy_grounding_rule(
        self,
        state: InvestigationState,
        citations: list[str],
    ) -> ComplianceRuleResult:
        has_policy_citation = bool(citations)
        return self._result(
            "policy_citation_grounding",
            "policy",
            has_policy_citation,
            "medium" if not has_policy_citation else "low",
            "Compliance reasoning checked for policy citation grounding.",
            citations,
            self._evidence_ids(state),
            0.78,
        )

    def _result(
        self,
        rule_id: str,
        category: str,
        passed: bool,
        severity: str,
        rationale: str,
        policy_refs: list[str],
        evidence_refs: list[str],
        confidence: float,
    ) -> ComplianceRuleResult:
        return {
            "rule_id": rule_id,
            "category": category,
            "passed": passed,
            "severity": severity,
            "rationale": rationale,
            "policy_refs": policy_refs,
            "evidence_refs": evidence_refs,
            "confidence": confidence,
        }

    def _policy_refs(self, state: InvestigationState) -> list[str]:
        return [
            citation["citation_id"]
            for citation in state.get("financial_retrieval", {}).get("citations", [])
        ]

    def _evidence_ids(self, state: InvestigationState) -> list[str]:
        return [item["evidence_id"] for item in state.get("evidence", [])]


class ComplianceAgentService:
    """Rule-based, citation-grounded compliance automation service."""

    def __init__(
        self,
        *,
        policy: CompliancePolicy | None = None,
        rule_engine: ComplianceRuleEngine | None = None,
    ) -> None:
        self._policy = policy or CompliancePolicy()
        self._rule_engine = rule_engine or ComplianceRuleEngine(self._policy)

    async def validate(self, state: InvestigationState) -> ComplianceValidationResult:
        rule_results = self._rule_engine.evaluate(state)
        citations = self._citations(state)
        flags = self._flags(rule_results)
        score = self._score(rule_results)
        confidence = self._confidence(rule_results, citations)
        recommendation = self._recommendation(score, flags, rule_results)
        passed = not any(
            not result["passed"] and result["severity"] in {"high", "critical"}
            for result in rule_results
        )

        return {
            "passed": passed,
            "compliance_score": score,
            "confidence": confidence,
            "flags": flags,
            "rule_results": rule_results,
            "citations": citations,
            "recommendation": recommendation,
            "suspicious_activity_summary": self._summary(flags, rule_results),
            "policy_version": self._policy.policy_version,
            "reasoning": self._reasoning(score, recommendation, rule_results),
            "metadata": {"rule_count": len(rule_results), "citation_count": len(citations)},
        }

    def _citations(self, state: InvestigationState) -> list[ComplianceCitation]:
        citations: list[ComplianceCitation] = []
        for citation in state.get("financial_retrieval", {}).get("citations", []):
            citations.append(
                {
                    "citation_id": citation["citation_id"],
                    "title": citation["title"],
                    "source_uri": citation["source_uri"],
                    "quote": citation["quote"],
                    "attribution": citation["attribution"],
                }
            )
        return citations

    def _flags(self, results: list[ComplianceRuleResult]) -> list[str]:
        flags: list[str] = []
        for result in results:
            if result["passed"]:
                continue
            if result["rule_id"] == "sanctions_jurisdiction_screen":
                flags.append("sanctions_hit")
            elif result["rule_id"] == "reporting_threshold_check":
                flags.append("sar_threshold_met")
            elif result["rule_id"] == "aml_suspicious_activity_review":
                flags.append("suspicious_activity_review_required")
            elif result["rule_id"] == "kyc_status_valid":
                flags.append("kyc_review_required")
            elif result["rule_id"] == "policy_citation_grounding":
                flags.append("policy_citation_required")
        return flags

    def _score(self, results: list[ComplianceRuleResult]) -> float:
        severity_weight = {"low": 4.0, "medium": 14.0, "high": 28.0, "critical": 45.0}
        score = 10.0
        for result in results:
            if not result["passed"]:
                score += severity_weight[result["severity"]] * result["confidence"]
        return round(min(score, 100.0), 2)

    def _confidence(
        self,
        results: list[ComplianceRuleResult],
        citations: list[ComplianceCitation],
    ) -> float:
        avg_rule_confidence = sum(result["confidence"] for result in results) / len(results)
        citation_bonus = min(0.15, len(citations) * 0.03)
        return round(min(0.97, avg_rule_confidence * 0.85 + citation_bonus), 2)

    def _recommendation(
        self,
        score: float,
        flags: list[str],
        results: list[ComplianceRuleResult],
    ) -> ComplianceRecommendation:
        if "sanctions_hit" in flags:
            return self._recommend(
                "block",
                "compliance_officer",
                "Sanctions hit requires block review.",
            )
        if "sar_threshold_met" in flags or "suspicious_activity_review_required" in flags:
            return self._recommend(
                "regulatory",
                "compliance_officer",
                "AML or threshold signal requires regulatory review.",
            )
        if "kyc_review_required" in flags or score >= 40:
            return self._recommend(
                "compliance_review",
                "compliance_analyst",
                "Compliance analyst review is required.",
            )
        if any(not result["passed"] for result in results):
            return self._recommend(
                "analyst_review",
                "risk_analyst",
                "Policy exception requires review.",
            )
        return self._recommend("none", "system", "No compliance escalation required.")

    def _recommend(
        self,
        level: str,
        role: str,
        rationale: str,
    ) -> ComplianceRecommendation:
        actions = {
            "block": ["place_temporary_hold", "senior_compliance_review"],
            "regulatory": ["prepare_sar_draft", "compliance_officer_review"],
            "compliance_review": ["review_kyc_and_policy_context"],
            "analyst_review": ["analyst_review"],
            "none": ["continue_standard_workflow"],
        }[level]
        return {
            "level": level,
            "required_role": role,
            "rationale": rationale,
            "recommended_actions": actions,
        }

    def _summary(
        self,
        flags: list[str],
        results: list[ComplianceRuleResult],
    ) -> str:
        failed = [result["rule_id"] for result in results if not result["passed"]]
        if not failed:
            return "Compliance validation found no material policy exceptions."
        return f"Compliance validation found {len(failed)} exceptions: {', '.join(failed)}."

    def _reasoning(
        self,
        score: float,
        recommendation: ComplianceRecommendation,
        results: list[ComplianceRuleResult],
    ) -> str:
        failed = [result["rationale"] for result in results if not result["passed"]]
        if not failed:
            return f"Compliance score {score}; no escalation recommended."
        return (
            f"Compliance score {score}; recommendation {recommendation['level']}. "
            + " ".join(failed[:3])
        )
