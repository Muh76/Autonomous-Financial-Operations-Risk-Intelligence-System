from pydantic import BaseModel, Field

from app.agents.state import RiskLevel


class OperationRequest(BaseModel):
    account_id: str
    operation_type: str = Field(examples=["invoice_payment", "treasury_transfer"])
    amount: float | None = Field(default=None, ge=0)
    currency: str = "USD"
    transaction_id: str | None = None


class OperationResponse(BaseModel):
    request_id: str
    risk_level: RiskLevel
    findings: list[str]
    recommended_actions: list[str]
