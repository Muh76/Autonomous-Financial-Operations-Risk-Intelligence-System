import pytest

from app.core.graph.financial_retrieval_node import financial_retrieval_node
from app.services.financial_retrieval import (
    FinancialRetrievalAgentService,
    default_financial_documents,
)

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_financial_retrieval_service_returns_citations_and_grounded_evidence() -> None:
    service = FinancialRetrievalAgentService()

    response = await service.retrieve(
        query="AML guidance for structuring and rapid movement escalation",
        documents=default_financial_documents(),
        document_types=["aml_guidance", "compliance_policy"],
    )

    assert response["results"]
    assert response["citations"]
    assert response["evidence"]
    assert response["confidence"] > 0
    assert response["citations"][0]["source_uri"]
    assert "citation" not in response["answer_summary"].lower()


@pytest.mark.asyncio
async def test_financial_retrieval_node_returns_langgraph_partial_state(low_risk_state) -> None:
    state = {
        **low_risk_state,
        "risk_band": "high",
        "fraud_typologies": ["structuring_signal", "rapid_chain_movement"],
        "compliance_flags": ["manual_compliance_review_required"],
    }

    result = await financial_retrieval_node(state)

    assert result["status"] == "compliance_validation"
    assert result["financial_retrieval"]["citations"]
    assert result["evidence"][0]["source_system"] == "financial_retrieval_agent"
    assert result["findings"][0]["source_node"] == "financial_retrieval"
    assert result["agent_executions"][0]["provider"] == "rag_retrieval_service"
