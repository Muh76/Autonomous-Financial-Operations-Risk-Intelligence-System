from operator import add
from typing import Annotated, Literal, NotRequired, TypedDict


EscalationLevel = Literal["none", "review", "escalate", "block"]


class InvestigationState(TypedDict):
    """Shared state for a financial transaction investigation workflow."""

    transaction_id: str
    findings: Annotated[list[str], add]
    risk_score: NotRequired[int]
    escalation_level: NotRequired[EscalationLevel]
    workflow_history: Annotated[list[str], add]
