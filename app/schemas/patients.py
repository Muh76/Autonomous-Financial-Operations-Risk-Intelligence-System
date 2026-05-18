from datetime import date
from uuid import UUID

from pydantic import Field

from app.schemas.common import ApiModel


class PatientCreate(ApiModel):
    external_id: str = Field(min_length=1, max_length=128)
    date_of_birth: date | None = None


class PatientRead(ApiModel):
    id: UUID
    external_id: str
    date_of_birth: date | None = None
