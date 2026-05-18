from uuid import uuid4

from app.schemas.patients import PatientCreate, PatientRead


class PatientService:
    async def list_patients(self) -> list[PatientRead]:
        return []

    async def create_patient(self, payload: PatientCreate) -> PatientRead:
        return PatientRead(
            id=uuid4(),
            external_id=payload.external_id,
            date_of_birth=payload.date_of_birth,
        )
