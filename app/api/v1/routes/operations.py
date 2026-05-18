from fastapi import APIRouter, Depends

from app.schemas.operations import OperationRequest, OperationResponse
from app.services.operations import OperationsService, get_operations_service

router = APIRouter()


@router.post("/analyze", response_model=OperationResponse)
async def analyze_operation(
    payload: OperationRequest,
    service: OperationsService = Depends(get_operations_service),
) -> OperationResponse:
    return await service.analyze(payload)
