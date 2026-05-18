from typing import Literal

from pydantic import Field

from app.schemas.common import ApiModel

SafetyLevel = Literal["low", "medium", "high", "critical"]


class SafetyAssessmentRequest(ApiModel):
    subject_id: str = Field(min_length=1, max_length=128)
    signal: str = Field(min_length=1, max_length=512)


class SafetyAssessmentResult(ApiModel):
    subject_id: str
    level: SafetyLevel
    action: str
