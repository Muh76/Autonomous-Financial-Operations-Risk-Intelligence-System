from typing import Annotated

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.services.evaluation import EvaluationService
from app.services.patients import PatientService
from app.services.safety import SafetyService


def get_request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if not isinstance(request_id, str):
        raise RuntimeError("request_id middleware is not configured")
    return request_id


def get_patient_service() -> PatientService:
    return PatientService()


def get_safety_service() -> SafetyService:
    return SafetyService()


def get_evaluation_service() -> EvaluationService:
    return EvaluationService()


SettingsDep = Annotated[Settings, Depends(get_settings)]
RequestIdDep = Annotated[str, Depends(get_request_id)]
PatientServiceDep = Annotated[PatientService, Depends(get_patient_service)]
SafetyServiceDep = Annotated[SafetyService, Depends(get_safety_service)]
EvaluationServiceDep = Annotated[EvaluationService, Depends(get_evaluation_service)]
