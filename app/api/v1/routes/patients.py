from fastapi import APIRouter, status

from app.api.dependencies import PatientServiceDep, RequestIdDep
from app.schemas.common import DataResponse
from app.schemas.patients import PatientCreate, PatientRead

router = APIRouter()


@router.get("", response_model=DataResponse[list[PatientRead]])
async def list_patients(
    service: PatientServiceDep,
    request_id: RequestIdDep,
) -> DataResponse[list[PatientRead]]:
    patients = await service.list_patients()
    return DataResponse(data=patients, request_id=request_id)


@router.post("", response_model=DataResponse[PatientRead], status_code=status.HTTP_201_CREATED)
async def create_patient(
    payload: PatientCreate,
    service: PatientServiceDep,
    request_id: RequestIdDep,
) -> DataResponse[PatientRead]:
    patient = await service.create_patient(payload)
    return DataResponse(data=patient, request_id=request_id)
