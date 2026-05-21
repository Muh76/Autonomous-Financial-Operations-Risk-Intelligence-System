import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.graph.compliance_agent_node import compliance_agent_node

WORKFLOW_VERSION = "financial-investigation-v1"
SCHEMA_VERSION = "investigation-state-v1"


async def main() -> None:
    state = {
        "case_id": "case_compliance_demo",
        "tenant_id": "demo",
        "thread_id": "thread_demo_compliance",
        "transaction_id": "txn_compliance_001",
        "workflow_version": WORKFLOW_VERSION,
        "schema_version": SCHEMA_VERSION,
        "status": "compliance_validation",
        "transaction_amount": 12_500.0,
        "transaction_currency": "USD",
        "jurisdiction": "US",
        "subject": {
            "customer_id": "cust_1",
            "account_ids": ["acct_1"],
            "kyc_status": "verified",
        },
        "fraud_detection": {
            "signals": ["structuring_signal", "rapid_chain_movement"],
        },
        "financial_retrieval": {
            "query": "AML policy structuring",
            "retrieval_intent": "compliance_validation",
            "results": [],
            "evidence": [],
            "citations": [
                {
                    "citation_id": "cite_aml_1",
                    "document_id": "aml_guidance_001",
                    "chunk_id": "chunk_1",
                    "title": "AML Monitoring Guidance",
                    "source_uri": "policy://aml/monitoring-guidance",
                    "document_type": "aml_guidance",
                    "quote": "AML programs should monitor structuring and rapid movement.",
                    "attribution": "AML Monitoring Guidance (Suspicious Activity Monitoring)",
                }
            ],
            "confidence": 0.72,
            "answer_summary": "AML policy evidence retrieved.",
            "source_attribution": ["AML Monitoring Guidance"],
            "recommended_actions": ["attach_citations"],
        },
        "evidence": [{"evidence_id": "ev_policy_1"}],
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

    result = await compliance_agent_node(state)
    compliance = result["compliance_validation"]
    print(
        {
            "passed": compliance["passed"],
            "score": compliance["compliance_score"],
            "flags": compliance["flags"],
            "recommendation": compliance["recommendation"]["level"],
        }
    )


if __name__ == "__main__":
    asyncio.run(main())
