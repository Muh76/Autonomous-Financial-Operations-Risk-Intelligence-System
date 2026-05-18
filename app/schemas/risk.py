from pydantic import BaseModel, Field

from app.agents.state import RiskLevel


class RiskAssessmentRequest(BaseModel):
    counterparty_id: str
    exposure_amount: float = Field(ge=0)
    limit_amount: float = Field(gt=0)
    currency: str = "USD"


class RiskAssessmentResponse(BaseModel):
    assessment_id: str
    risk_score: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    rationale: list[str]
