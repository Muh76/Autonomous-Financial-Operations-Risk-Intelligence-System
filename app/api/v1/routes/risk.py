from fastapi import APIRouter, Depends

from app.schemas.risk import RiskAssessmentRequest, RiskAssessmentResponse
from app.services.risk import RiskService, get_risk_service

router = APIRouter()


@router.post("/assess", response_model=RiskAssessmentResponse)
async def assess_risk(
    payload: RiskAssessmentRequest,
    service: RiskService = Depends(get_risk_service),
) -> RiskAssessmentResponse:
    return await service.assess(payload)
