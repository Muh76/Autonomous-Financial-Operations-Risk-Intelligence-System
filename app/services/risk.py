from uuid import uuid4

from app.schemas.risk import RiskAssessmentRequest, RiskAssessmentResponse


class RiskService:
    async def assess(self, payload: RiskAssessmentRequest) -> RiskAssessmentResponse:
        score = min(100, int((payload.exposure_amount / max(payload.limit_amount, 1)) * 100))
        level = "critical" if score >= 90 else "high" if score >= 70 else "medium" if score >= 40 else "low"
        return RiskAssessmentResponse(
            assessment_id=str(uuid4()),
            risk_score=score,
            risk_level=level,
            rationale=[
                "Assessment uses exposure-to-limit ratio placeholder.",
                "Replace with policy, market, counterparty, and anomaly signals.",
            ],
        )


def get_risk_service() -> RiskService:
    return RiskService()
