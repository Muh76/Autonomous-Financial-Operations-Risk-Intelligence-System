from typing import Literal, NotRequired, TypedDict


TransactionPatternType = Literal[
    "high_velocity",
    "structuring",
    "round_amount",
    "rapid_movement",
    "counterparty_concentration",
    "cross_border",
    "chain_depth",
    "unusual_time",
]


class TransactionObservation(TypedDict):
    """Normalized transaction event used by the transaction analysis agent."""

    transaction_id: str
    amount: float
    currency: str
    occurred_at: str
    account_id: NotRequired[str]
    counterparty_id: NotRequired[str]
    direction: NotRequired[Literal["inbound", "outbound"]]
    jurisdiction: NotRequired[str]
    channel: NotRequired[str]
    device_id: NotRequired[str]


class TransactionAggregate(TypedDict):
    """Aggregate metrics over a transaction window."""

    transaction_count: int
    total_amount: float
    average_amount: float
    max_amount: float
    currency: str
    unique_counterparties: int
    inbound_amount: float
    outbound_amount: float


class TemporalAnalysis(TypedDict):
    """Time-window signals for activity velocity and unusual timing."""

    first_seen_at: str
    last_seen_at: str
    window_minutes: float
    transactions_per_hour: float
    burst_count: int
    unusual_hour_count: int


class TransactionChainHop(TypedDict):
    """One hop in a transaction chain used for flow analysis."""

    from_entity: str
    to_entity: str
    transaction_id: str
    amount: float
    occurred_at: str


class SuspiciousActivityIndicator(TypedDict):
    """Structured indicator emitted by transaction analysis heuristics."""

    indicator: TransactionPatternType
    severity: Literal["low", "medium", "high", "critical"]
    description: str
    evidence_transaction_ids: list[str]
    confidence: float


class TransactionAnalysisResult(TypedDict):
    """Typed response schema for the transaction analysis agent."""

    transaction_id: str
    aggregate: TransactionAggregate
    temporal: TemporalAnalysis
    chain: list[TransactionChainHop]
    indicators: list[SuspiciousActivityIndicator]
    anomaly_score: float
    confidence: float
    summary: str
    recommended_actions: list[str]
