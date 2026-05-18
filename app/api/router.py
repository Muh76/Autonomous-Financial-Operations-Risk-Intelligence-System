from fastapi import APIRouter

from app.api.v1.routes import operations, risk

api_router = APIRouter()
api_router.include_router(operations.router, prefix="/operations", tags=["operations"])
api_router.include_router(risk.router, prefix="/risk", tags=["risk"])
