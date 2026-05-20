"""Application service layer.

Service exports are loaded lazily so lightweight modules can be imported without requiring every
optional infrastructure dependency, such as Redis or SQLAlchemy, to be installed in local scripts.
"""

from typing import Any

__all__ = [
    "AgentMemoryRequest",
    "ApprovalCheckpointService",
    "ApprovalDecisionRequest",
    "EvidenceGroundingPipeline",
    "FinancialDocumentIngestionPipeline",
    "FinancialRetrievalAgentService",
    "FinancialReranker",
    "FraudDetectionPolicy",
    "FraudDetectionService",
    "FraudNarrativeProvider",
    "HashingEmbeddingProvider",
    "InMemoryVectorRetrievalLayer",
    "RetrievalPolicy",
    "RiskScoringPolicy",
    "RiskScoringService",
    "TransactionAnalysisPolicy",
    "TransactionAnalysisService",
    "WorkflowMemoryService",
    "WorkflowVisualizationService",
    "latest_approval_states",
]


def __getattr__(name: str) -> Any:
    if name in {"ApprovalCheckpointService", "ApprovalDecisionRequest", "latest_approval_states"}:
        from app.services.approval_checkpoints import (
            ApprovalCheckpointService,
            ApprovalDecisionRequest,
            latest_approval_states,
        )

        values = {
            "ApprovalCheckpointService": ApprovalCheckpointService,
            "ApprovalDecisionRequest": ApprovalDecisionRequest,
            "latest_approval_states": latest_approval_states,
        }
        return values[name]

    if name in {"TransactionAnalysisPolicy", "TransactionAnalysisService"}:
        from app.services.transaction_analysis import (
            TransactionAnalysisPolicy,
            TransactionAnalysisService,
        )

        values = {
            "TransactionAnalysisPolicy": TransactionAnalysisPolicy,
            "TransactionAnalysisService": TransactionAnalysisService,
        }
        return values[name]

    if name in {"FraudDetectionPolicy", "FraudDetectionService", "FraudNarrativeProvider"}:
        from app.services.fraud_detection import (
            FraudDetectionPolicy,
            FraudDetectionService,
            FraudNarrativeProvider,
        )

        values = {
            "FraudDetectionPolicy": FraudDetectionPolicy,
            "FraudDetectionService": FraudDetectionService,
            "FraudNarrativeProvider": FraudNarrativeProvider,
        }
        return values[name]

    if name in {
        "EvidenceGroundingPipeline",
        "FinancialDocumentIngestionPipeline",
        "FinancialRetrievalAgentService",
        "FinancialReranker",
        "HashingEmbeddingProvider",
        "InMemoryVectorRetrievalLayer",
        "RetrievalPolicy",
    }:
        from app.services.financial_retrieval import (
            EvidenceGroundingPipeline,
            FinancialDocumentIngestionPipeline,
            FinancialRetrievalAgentService,
            FinancialReranker,
            HashingEmbeddingProvider,
            InMemoryVectorRetrievalLayer,
            RetrievalPolicy,
        )

        values = {
            "EvidenceGroundingPipeline": EvidenceGroundingPipeline,
            "FinancialDocumentIngestionPipeline": FinancialDocumentIngestionPipeline,
            "FinancialRetrievalAgentService": FinancialRetrievalAgentService,
            "FinancialReranker": FinancialReranker,
            "HashingEmbeddingProvider": HashingEmbeddingProvider,
            "InMemoryVectorRetrievalLayer": InMemoryVectorRetrievalLayer,
            "RetrievalPolicy": RetrievalPolicy,
        }
        return values[name]

    if name in {"RiskScoringPolicy", "RiskScoringService"}:
        from app.services.risk_scoring import RiskScoringPolicy, RiskScoringService

        values = {
            "RiskScoringPolicy": RiskScoringPolicy,
            "RiskScoringService": RiskScoringService,
        }
        return values[name]

    if name == "WorkflowVisualizationService":
        from app.services.workflow_visualization import WorkflowVisualizationService

        return WorkflowVisualizationService

    if name in {"AgentMemoryRequest", "WorkflowMemoryService"}:
        from app.services.workflow_memory import AgentMemoryRequest, WorkflowMemoryService

        values = {
            "AgentMemoryRequest": AgentMemoryRequest,
            "WorkflowMemoryService": WorkflowMemoryService,
        }
        return values[name]

    raise AttributeError(f"module 'app.services' has no attribute {name!r}")
