from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import mean

from app.core.graph.state_schemas import (
    SuspiciousActivityIndicator,
    TemporalAnalysis,
    TransactionAggregate,
    TransactionAnalysisResult,
    TransactionChainHop,
    TransactionObservation,
)


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


@dataclass(frozen=True)
class TransactionAnalysisPolicy:
    high_value_threshold: float = 10_000.0
    structuring_threshold: float = 10_000.0
    structuring_margin: float = 500.0
    velocity_count_threshold: int = 5
    velocity_window_minutes: float = 60.0
    burst_gap_minutes: float = 10.0
    counterparty_concentration_ratio: float = 0.65
    chain_depth_threshold: int = 3
    unusual_start_hour: int = 0
    unusual_end_hour: int = 5


class TransactionAnalysisService:
    """Async-ready deterministic transaction analysis agent service."""

    def __init__(self, policy: TransactionAnalysisPolicy | None = None) -> None:
        self._policy = policy or TransactionAnalysisPolicy()

    async def analyze(
        self,
        *,
        transaction_id: str,
        transactions: list[TransactionObservation],
    ) -> TransactionAnalysisResult:
        observations = self._normalize(transaction_id, transactions)
        aggregate = self._aggregate(observations)
        temporal = self._temporal(observations)
        chain = self._chain(observations)
        indicators = self._indicators(observations, aggregate, temporal, chain)
        anomaly_score = self._score(indicators, aggregate, temporal, chain)
        confidence = self._confidence(observations, indicators)

        return {
            "transaction_id": transaction_id,
            "aggregate": aggregate,
            "temporal": temporal,
            "chain": chain,
            "indicators": indicators,
            "anomaly_score": anomaly_score,
            "confidence": confidence,
            "summary": self._summary(indicators, anomaly_score),
            "recommended_actions": self._recommended_actions(anomaly_score, indicators),
        }

    def _normalize(
        self,
        transaction_id: str,
        transactions: list[TransactionObservation],
    ) -> list[TransactionObservation]:
        if not transactions:
            now = _iso(datetime.now(tz=timezone.utc))
            return [
                {
                    "transaction_id": transaction_id,
                    "amount": 0.0,
                    "currency": "USD",
                    "occurred_at": now,
                    "direction": "outbound",
                }
            ]
        return sorted(transactions, key=lambda item: item["occurred_at"])

    def _aggregate(self, transactions: list[TransactionObservation]) -> TransactionAggregate:
        amounts = [float(item["amount"]) for item in transactions]
        currency = transactions[-1]["currency"]
        inbound = sum(
            float(item["amount"]) for item in transactions if item.get("direction") == "inbound"
        )
        outbound = sum(
            float(item["amount"]) for item in transactions if item.get("direction") != "inbound"
        )
        counterparties = {
            item["counterparty_id"] for item in transactions if item.get("counterparty_id")
        }
        return {
            "transaction_count": len(transactions),
            "total_amount": round(sum(amounts), 2),
            "average_amount": round(mean(amounts), 2),
            "max_amount": round(max(amounts), 2),
            "currency": currency,
            "unique_counterparties": len(counterparties),
            "inbound_amount": round(inbound, 2),
            "outbound_amount": round(outbound, 2),
        }

    def _temporal(self, transactions: list[TransactionObservation]) -> TemporalAnalysis:
        timestamps = [_parse_timestamp(item["occurred_at"]) for item in transactions]
        first_seen = min(timestamps)
        last_seen = max(timestamps)
        window_minutes = max((last_seen - first_seen).total_seconds() / 60.0, 1.0)
        burst_count = 0
        for previous, current in zip(timestamps, timestamps[1:]):
            gap_minutes = (current - previous).total_seconds() / 60.0
            if gap_minutes <= self._policy.burst_gap_minutes:
                burst_count += 1
        unusual_count = sum(
            1
            for item in timestamps
            if self._policy.unusual_start_hour <= item.hour <= self._policy.unusual_end_hour
        )
        return {
            "first_seen_at": _iso(first_seen),
            "last_seen_at": _iso(last_seen),
            "window_minutes": round(window_minutes, 2),
            "transactions_per_hour": round(len(transactions) / (window_minutes / 60.0), 2),
            "burst_count": burst_count,
            "unusual_hour_count": unusual_count,
        }

    def _chain(self, transactions: list[TransactionObservation]) -> list[TransactionChainHop]:
        hops: list[TransactionChainHop] = []
        for item in transactions:
            account_id = item.get("account_id", "unknown_account")
            counterparty_id = item.get("counterparty_id", "unknown_counterparty")
            if item.get("direction") == "inbound":
                from_entity = counterparty_id
                to_entity = account_id
            else:
                from_entity = account_id
                to_entity = counterparty_id
            hops.append(
                {
                    "from_entity": from_entity,
                    "to_entity": to_entity,
                    "transaction_id": item["transaction_id"],
                    "amount": float(item["amount"]),
                    "occurred_at": item["occurred_at"],
                }
            )
        return hops

    def _indicators(
        self,
        transactions: list[TransactionObservation],
        aggregate: TransactionAggregate,
        temporal: TemporalAnalysis,
        chain: list[TransactionChainHop],
    ) -> list[SuspiciousActivityIndicator]:
        indicators: list[SuspiciousActivityIndicator] = []
        transaction_ids = [item["transaction_id"] for item in transactions]
        near_threshold = [
            item["transaction_id"]
            for item in transactions
            if self._policy.structuring_threshold - self._policy.structuring_margin
            <= float(item["amount"])
            < self._policy.structuring_threshold
        ]

        if temporal["transactions_per_hour"] >= self._policy.velocity_count_threshold:
            indicators.append(
                self._indicator(
                    "high_velocity",
                    "high",
                    "Transaction velocity exceeds configured hourly threshold.",
                    transaction_ids,
                    0.82,
                )
            )
        if len(near_threshold) >= 2:
            indicators.append(
                self._indicator(
                    "structuring",
                    "critical",
                    "Multiple transactions sit just below reporting threshold.",
                    near_threshold,
                    0.88,
                )
            )
        if any(float(item["amount"]) % 1000 == 0 for item in transactions):
            indicators.append(
                self._indicator(
                    "round_amount",
                    "medium",
                    "Round amount transaction pattern detected.",
                    transaction_ids,
                    0.64,
                )
            )
        if temporal["burst_count"] >= 2:
            indicators.append(
                self._indicator(
                    "rapid_movement",
                    "high",
                    "Multiple transactions occurred within a short burst window.",
                    transaction_ids,
                    0.8,
                )
            )

        counterparty_counts = Counter(
            item["counterparty_id"] for item in transactions if item.get("counterparty_id")
        )
        if counterparty_counts:
            _, count = counterparty_counts.most_common(1)[0]
            concentration = count / len(transactions)
            if concentration >= self._policy.counterparty_concentration_ratio:
                indicators.append(
                    self._indicator(
                        "counterparty_concentration",
                        "medium",
                        "Transactions are concentrated around one counterparty.",
                        transaction_ids,
                        0.72,
                    )
                )

        jurisdictions = {
            item.get("jurisdiction") for item in transactions if item.get("jurisdiction")
        }
        if len(jurisdictions) > 1:
            indicators.append(
                self._indicator(
                    "cross_border",
                    "medium",
                    "Transactions span multiple jurisdictions.",
                    transaction_ids,
                    0.68,
                )
            )
        if len(chain) >= self._policy.chain_depth_threshold:
            indicators.append(
                self._indicator(
                    "chain_depth",
                    "medium",
                    "Transaction chain depth exceeds review threshold.",
                    transaction_ids,
                    0.7,
                )
            )
        if temporal["unusual_hour_count"] > 0:
            indicators.append(
                self._indicator(
                    "unusual_time",
                    "low",
                    "Activity occurred during unusual overnight hours.",
                    transaction_ids,
                    0.58,
                )
            )
        return indicators

    def _indicator(
        self,
        indicator: str,
        severity: str,
        description: str,
        evidence_transaction_ids: list[str],
        confidence: float,
    ) -> SuspiciousActivityIndicator:
        return {
            "indicator": indicator,
            "severity": severity,
            "description": description,
            "evidence_transaction_ids": evidence_transaction_ids,
            "confidence": confidence,
        }

    def _score(
        self,
        indicators: list[SuspiciousActivityIndicator],
        aggregate: TransactionAggregate,
        temporal: TemporalAnalysis,
        chain: list[TransactionChainHop],
    ) -> float:
        severity_weight = {"low": 8.0, "medium": 15.0, "high": 25.0, "critical": 38.0}
        score = 10.0
        score += min(20.0, aggregate["total_amount"] / 2500.0)
        score += min(15.0, temporal["transactions_per_hour"] * 1.5)
        score += min(10.0, len(chain) * 1.25)
        score += sum(
            severity_weight[item["severity"]] * item["confidence"] for item in indicators
        )
        return round(min(score, 100.0), 2)

    def _confidence(
        self,
        transactions: list[TransactionObservation],
        indicators: list[SuspiciousActivityIndicator],
    ) -> float:
        evidence_factor = min(0.25, len(transactions) * 0.03)
        indicator_factor = min(0.2, len(indicators) * 0.025)
        return round(min(0.55 + evidence_factor + indicator_factor, 0.96), 2)

    def _summary(
        self,
        indicators: list[SuspiciousActivityIndicator],
        anomaly_score: float,
    ) -> str:
        if not indicators:
            return (
                "Transaction analysis found no material suspicious indicators; "
                f"score {anomaly_score}."
            )
        labels = ", ".join(item["indicator"] for item in indicators[:4])
        return (
            f"Transaction analysis found {len(indicators)} indicators: {labels}; "
            f"score {anomaly_score}."
        )

    def _recommended_actions(
        self,
        anomaly_score: float,
        indicators: list[SuspiciousActivityIndicator],
    ) -> list[str]:
        indicator_names = {item["indicator"] for item in indicators}
        actions: list[str] = []
        if anomaly_score >= 80 or "structuring" in indicator_names:
            actions.extend(["expand_evidence", "senior_review"])
        elif anomaly_score >= 50:
            actions.append("analyst_review")
        else:
            actions.append("continue_standard_workflow")
        if "chain_depth" in indicator_names or "rapid_movement" in indicator_names:
            actions.append("trace_transaction_chain")
        if "cross_border" in indicator_names:
            actions.append("validate_cross_border_policy")
        return actions
