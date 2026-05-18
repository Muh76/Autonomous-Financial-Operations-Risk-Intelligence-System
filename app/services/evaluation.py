from app.schemas.evaluation import EvaluationRequest, EvaluationResult


class EvaluationService:
    async def run(self, payload: EvaluationRequest) -> EvaluationResult:
        return EvaluationResult(
            dataset_id=payload.dataset_id,
            evaluator=payload.evaluator,
            accepted=True,
            score=1.0,
        )
