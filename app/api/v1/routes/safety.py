from fastapi import APIRouter

from app.api.dependencies import RequestIdDep, SafetyServiceDep
from app.schemas.common import DataResponse
from app.schemas.safety import SafetyAssessmentRequest, SafetyAssessmentResult

router = APIRouter()


@router.post("", response_model=DataResponse[SafetyAssessmentResult])
async def assess_safety(
    payload: SafetyAssessmentRequest,
    service: SafetyServiceDep,
    request_id: RequestIdDep,
) -> DataResponse[SafetyAssessmentResult]:
    result = await service.assess(payload)
    return DataResponse(data=result, request_id=request_id)
