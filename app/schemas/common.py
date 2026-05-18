from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

DataT = TypeVar("DataT")


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


class HealthResponse(BaseResponse):
    status: str
    environment: str
    database: str
    redis: str
