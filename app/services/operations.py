from uuid import uuid4

from app.agents.graph import build_financial_operations_graph
from app.agents.state import FinancialOperationState
from app.schemas.operations import OperationRequest, OperationResponse


class OperationsService:
    def __init__(self) -> None:
        self._graph = build_financial_operations_graph()

    async def analyze(self, payload: OperationRequest) -> OperationResponse:
        initial_state: FinancialOperationState = {
            "request_id": str(uuid4()),
            "account_id": payload.account_id,
            "transaction_id": payload.transaction_id,
            "amount": payload.amount,
            "currency": payload.currency,
            "operation_type": payload.operation_type,
            "findings": [],
            "recommended_actions": [],
        }
        result = await self._graph.ainvoke(initial_state)
        return OperationResponse(
            request_id=result["request_id"],
            risk_level=result["risk_level"],
            findings=result.get("findings", []),
            recommended_actions=result.get("recommended_actions", []),
        )


def get_operations_service() -> OperationsService:
    return OperationsService()
