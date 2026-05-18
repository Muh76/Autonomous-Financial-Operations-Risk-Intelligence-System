from pydantic import Field

from app.schemas.common import ApiModel


class EvaluationRequest(ApiModel):
    dataset_id: str = Field(min_length=1, max_length=128)
    evaluator: str = Field(min_length=1, max_length=128)


class EvaluationResult(ApiModel):
    dataset_id: str
    evaluator: str
    accepted: bool
    score: float
