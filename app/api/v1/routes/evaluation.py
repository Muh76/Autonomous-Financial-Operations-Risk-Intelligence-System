from fastapi import APIRouter

from app.api.dependencies import EvaluationServiceDep, RequestIdDep
from app.schemas.common import DataResponse
from app.schemas.evaluation import EvaluationRequest, EvaluationResult

router = APIRouter()


@router.post("", response_model=DataResponse[EvaluationResult])
async def run_evaluation(
    payload: EvaluationRequest,
    service: EvaluationServiceDep,
    request_id: RequestIdDep,
) -> DataResponse[EvaluationResult]:
    result = await service.run(payload)
    return DataResponse(data=result, request_id=request_id)
