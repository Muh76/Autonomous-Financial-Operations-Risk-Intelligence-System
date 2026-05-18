from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.common import ErrorDetail, ErrorResponse


class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        code: str = "application_error",
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.code = code


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return _error_response(
            request=request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _error_response(
            request=request,
            status_code=exc.status_code,
            code="http_error",
            message=str(exc.detail),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return _error_response(
            request=request,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="validation_error",
            message="Request validation failed",
            details=[
                ErrorDetail(field=".".join(map(str, error["loc"])), message=error["msg"])
                for error in exc.errors()
            ],
        )


def _error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
    details: list[ErrorDetail] | None = None,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    body = ErrorResponse(
        success=False,
        error=ErrorDetail(code=code, message=message),
        details=details or [],
        request_id=request_id if isinstance(request_id, str) else None,
    )
    return JSONResponse(status_code=status_code, content=body.model_dump(exclude_none=True))
