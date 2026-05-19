from typing import Literal


RiskBand = Literal["low", "medium", "high", "critical"]
EscalationLevel = Literal["none", "analyst_review", "senior_review", "regulatory", "block"]
FindingCategory = Literal["transaction", "fraud", "compliance", "risk", "critic", "report"]
WorkflowEventStatus = Literal["started", "completed", "failed", "fallback", "routed", "interrupted"]
NodeExecutionStatus = Literal["success", "failed", "retrying", "fallback", "skipped"]
ApprovalStatus = Literal["not_required", "pending", "approved", "rejected"]
EvidenceType = Literal[
    "transaction_snapshot",
    "customer_profile",
    "account_history",
    "merchant_profile",
    "relationship_graph",
    "external_intelligence",
    "expanded_context",
    "analyst_note",
]
AgentRole = Literal[
    "transaction_investigator",
    "fraud_analyst",
    "compliance_reviewer",
    "risk_scorer",
    "critic",
    "report_writer",
]
CaseStatus = Literal[
    "initialized",
    "enriching",
    "fraud_analysis",
    "compliance_validation",
    "risk_scoring",
    "critic_validation",
    "evidence_expansion",
    "awaiting_human_approval",
    "reporting",
    "closed",
    "failed",
]
WorkflowRoute = Literal[
    "report_generation",
    "evidence_expansion",
    "escalation_router",
    "human_approval_checkpoint",
    "workflow_failure",
]
