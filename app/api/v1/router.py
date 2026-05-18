from fastapi import APIRouter

from app.api.v1.routes import evaluation, patients, safety

router = APIRouter()
router.include_router(patients.router, prefix="/patients", tags=["patients"])
router.include_router(safety.router, prefix="/safety", tags=["safety"])
router.include_router(evaluation.router, prefix="/evaluation", tags=["evaluation"])
