from typing import Literal, TypedDict


RiskLevel = Literal["low", "medium", "high", "critical"]


class FinancialOperationState(TypedDict, total=False):
    request_id: str
    account_id: str
    transaction_id: str | None
    amount: float | None
    currency: str
    operation_type: str
    risk_level: RiskLevel
    findings: list[str]
    recommended_actions: list[str]
