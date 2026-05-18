from typing import Literal, TypedDict


RiskLevel = Literal["low", "medium", "high", "critical"]


class RiskWorkflowState(TypedDict):
    """State passed between risk intelligence workflow nodes."""

    operation_id: str
    amount: float
    currency: str
    risk_level: RiskLevel | None
    decision: str | None
