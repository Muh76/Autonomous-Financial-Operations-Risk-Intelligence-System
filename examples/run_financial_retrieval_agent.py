import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.graph.financial_retrieval_node import financial_retrieval_node

WORKFLOW_VERSION = "financial-investigation-v1"
SCHEMA_VERSION = "investigation-state-v1"


async def main() -> None:
    state = {
        "case_id": "case_retrieval_demo",
        "tenant_id": "demo",
        "thread_id": "thread_demo_retrieval",
        "transaction_id": "txn_retrieval_001",
        "workflow_version": WORKFLOW_VERSION,
        "schema_version": SCHEMA_VERSION,
        "status": "initialized",
        "risk_band": "high",
        "fraud_typologies": ["structuring_signal", "rapid_chain_movement"],
        "compliance_flags": ["manual_compliance_review_required"],
        "evidence": [],
        "findings": [],
        "workflow_history": [],
        "node_errors": [],
        "approvals": [],
        "escalations": [],
        "node_results": [],
        "agent_executions": [],
        "node_traces": [],
        "edge_traversals": [],
        "timeline_events": [],
        "retry_counts": {},
        "retry_state": {},
        "fallback_used": {},
    }

    result = await financial_retrieval_node(state)
    retrieval = result["financial_retrieval"]
    print(
        {
            "confidence": retrieval["confidence"],
            "citations": retrieval["source_attribution"],
            "evidence_count": len(retrieval["evidence"]),
            "recommended_actions": retrieval["recommended_actions"],
        }
    )


if __name__ == "__main__":
    asyncio.run(main())
