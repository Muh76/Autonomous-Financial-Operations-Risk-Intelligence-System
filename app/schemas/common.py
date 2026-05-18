from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

DataT = TypeVar("DataT")
HealthStatus = Literal["ok", "degraded", "failed"]


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ErrorDetail(ApiModel):
    message: str
    code: str | None = None
    field: str | None = None


class BaseResponse(ApiModel):
    success: bool = True
    request_id: str | None = None


class DataResponse(BaseResponse, Generic[DataT]):
    data: DataT


class ErrorResponse(BaseResponse):
    success: bool = False
    error: ErrorDetail
    details: list[ErrorDetail] = Field(default_factory=list)


class HealthComponent(ApiModel):
    status: HealthStatus
    latency_ms: float
    detail: str | None = None


class HealthResponse(BaseResponse):
    status: HealthStatus
    environment: str
    version: str
    components: dict[str, HealthComponent]
